# app/services/admin_school.py
from __future__ import annotations
from typing import Iterable, Sequence
from sqlalchemy import select, update
from app.extensions import db
from app.models.school import School
from app.models.admin_school_map import AdminSchoolMap

def ensure_schools_exist_or_400(ids: Sequence[str]):
    """DB 校验：所有 id 必须存在且未删除；否则抛 400（你也可以抛 ValidationError 走统一返回）。"""
    if not ids:
        return
    rows = db.session.execute(
        select(School.id).where(School.is_deleted.is_(False), School.id.in_(list(ids)))
    ).scalars().all()
    ok = set(rows)
    missing = [sid for sid in ids if sid not in ok]
    if missing:
        from app.utils.responses import fail, ApiCodes
        # 你也可以 raise ValidationError({"school_ids": [...]})
        raise RuntimeError(f"学校不存在或已删除: {', '.join(missing)}")

def bind_schools_to_admin(aid: str, ids: Iterable[str]):
    """创建阶段绑定：只插入新增的、忽略已存在的（软删的会恢复）。不 commit。"""
    ids = list(set(ids)) if ids else []
    if not ids:
        return 0

    # 查现状（含软删）
    rows = db.session.execute(
        select(AdminSchoolMap.school_id, AdminSchoolMap.is_deleted)
        .where(AdminSchoolMap.admin_id == aid, AdminSchoolMap.school_id.in_(ids))
    ).all()
    exists_active = {sid for sid, d in rows if d is False}
    exists_deleted = {sid for sid, d in rows if d is True}

    to_reactivate = list(exists_deleted)
    to_insert = [sid for sid in ids if sid not in exists_active and sid not in exists_deleted]

    # 恢复软删
    if to_reactivate:
        db.session.execute(
            update(AdminSchoolMap)
            .where(AdminSchoolMap.admin_id == aid, AdminSchoolMap.school_id.in_(to_reactivate))
            .values(is_deleted=False)
        )

    # 批量插入
    if to_insert:
        db.session.bulk_save_objects([AdminSchoolMap(admin_id=aid, school_id=sid) for sid in to_insert])

    return len(to_reactivate) + len(to_insert)

def replace_admin_schools(aid: str, new_ids: Sequence[str]):
    """更新阶段全量替换：新增 + 恢复 + 软删多余。返回（添加数, 恢复数, 删除数）。不 commit。"""
    new_set = set(new_ids or [])

    # 查该管理员的所有映射
    rows = db.session.execute(
        select(AdminSchoolMap.school_id, AdminSchoolMap.is_deleted)
        .where(AdminSchoolMap.admin_id == aid)
    ).all()
    active = {sid for sid, d in rows if d is False}
    deleted = {sid for sid, d in rows if d is True}

    to_add = list(new_set - active - deleted)
    to_reactivate = list(new_set & deleted)
    to_soft_delete = list(active - new_set)

    if to_reactivate:
        db.session.execute(
            update(AdminSchoolMap)
            .where(AdminSchoolMap.admin_id == aid, AdminSchoolMap.school_id.in_(to_reactivate))
            .values(is_deleted=False)
        )
    if to_soft_delete:
        db.session.execute(
            update(AdminSchoolMap)
            .where(AdminSchoolMap.admin_id == aid, AdminSchoolMap.school_id.in_(to_soft_delete))
            .values(is_deleted=True)
        )
    if to_add:
        db.session.bulk_save_objects([AdminSchoolMap(admin_id=aid, school_id=sid) for sid in to_add])

    return len(to_add), len(to_reactivate), len(to_soft_delete)
