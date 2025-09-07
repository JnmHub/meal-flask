# app/blueprints/schools.py
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy import or_

from app.blueprints import schools_bp
from app.models import AdminSchoolMap
from app.utils.responses import success, fail, ApiCodes
from app.utils.pagination import get_pagination, page_result
from app.extensions import db
from app.models.school import School
from app.schemas.school import SchoolCreateSchema, SchoolUpdateSchema, SchoolOutSchema

# 复用管理员权限装饰器（你如果已经抽到 utils 里就从那里 import）
from app.blueprints.admins import admin_required  # 若担心循环依赖，可把装饰器挪到 utils/authz.py
from app.utils.security import is_super_id

school_out = SchoolOutSchema()
school_out_many = SchoolOutSchema(many=True)

@schools_bp.get('')
@jwt_required()
def list_schools():
    """
    分页查询：
    支持 ?page=1&size=10 或 ?current=1&pageSize=10
    关键字：?kw=xxx（模糊匹配 name/alias）
    返回结构：{records, total, size, current, pages}
    """
    uid = str(get_jwt_identity() or "")
    print(get_jwt_identity())
    is_super = is_super_id(uid)
    page, size = get_pagination()
    kw = (request.args.get('kw') or '').strip()

    if is_super:
        q = School.query.filter(School.is_deleted.is_(False))
    else:
        # 只取该管理员被绑定的学校
        q = (School.query
             .join(AdminSchoolMap, AdminSchoolMap.school_id == School.id)
             .filter(
                 School.is_deleted.is_(False),
                 AdminSchoolMap.is_deleted.is_(False),
                 AdminSchoolMap.admin_id == uid
             )
             .distinct(School.id))  # 防重复

    if kw:
        q = q.filter(or_(
            School.name.ilike(f'%{kw}%'),
            School.alias.ilike(f'%{kw}%')
        ))

    q = q.order_by(School.created_at.desc())
    p = q.paginate(page=page, per_page=size, error_out=False)

    data = page_result(p, school_out_many.dump(p.items))
    return success(data)


@schools_bp.get('/<string:sid>')
@jwt_required()
def get_school(sid: str):
    s = School.query.filter_by(id=sid, is_deleted=False).first()
    if not s:
        return fail(ApiCodes.NOT_FOUND, "学校不存在")
    return success(school_out.dump(s))


@schools_bp.post('')
@admin_required
def create_school():
    json_data = request.get_json(silent=True)
    if json_data is None:
        return fail(ApiCodes.BAD_REQUEST, "请求体必须为 JSON（Content-Type: application/json）")
    try:
        data = SchoolCreateSchema().load(json_data)  # ✅ 中文校验提示
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    # 唯一性检查（未删除）
    exists = School.query.filter(
        School.is_deleted.is_(False),
        or_(School.name == data['name'], School.alias == data['alias'])
    ).first()
    if exists:
        return fail(ApiCodes.CONFLICT, "学校名称或别名已存在")

    s = School(name=data['name'], alias=data['alias'])
    db.session.add(s)
    db.session.commit()
    return success(school_out.dump(s))


@schools_bp.put('/<string:sid>')
@admin_required
def update_school(sid: str):
    json_data = request.get_json(silent=True) or {}
    try:
        data = SchoolUpdateSchema().load(json_data, partial=True)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    s = School.query.filter_by(id=sid, is_deleted=False).first()
    if not s:
        return fail(ApiCodes.NOT_FOUND, "学校不存在")

    # 冲突检查
    if 'name' in data:
        dup = School.query.filter(
            School.is_deleted.is_(False),
            School.name == data['name'],
            School.id != sid
        ).first()
        if dup:
            return fail(ApiCodes.CONFLICT, "学校名称已存在")
        s.name = data['name']

    if 'alias' in data:
        dup = School.query.filter(
            School.is_deleted.is_(False),
            School.alias == data['alias'],
            School.id != sid
        ).first()
        if dup:
            return fail(ApiCodes.CONFLICT, "别名已存在")
        s.alias = data['alias']

    db.session.commit()
    return success(school_out.dump(s))


@schools_bp.delete('/<string:sid>')
@admin_required
def delete_school(sid: str):
    s = School.query.filter_by(id=sid, is_deleted=False).first()
    if not s:
        return fail(ApiCodes.NOT_FOUND, "学校不存在")
    s.soft_delete()
    db.session.commit()
    return success({"id": sid}, "已删除")
