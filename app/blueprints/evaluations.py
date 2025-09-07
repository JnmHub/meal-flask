# app/blueprints/evaluations.py
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload, selectinload
from marshmallow import ValidationError

from app.blueprints import evaluations_bp
from app.models.evaluation import Evaluation, EvaluationCategory
from app.schemas.evaluation import EvaluationSchema, EvaluationCategorySchema, EvaluationCreateSchema, \
    StudentEvaluationCreateSchema
from app.utils.responses import success, fail, ApiCodes
from app.utils.pagination import get_pagination, page_result
from app.extensions import db
from app.blueprints.admins import admin_required
from app.utils.security import is_super_id
from app.models import AdminSchoolMap, Student, School

# 创建一个名为 'evaluations' 的新蓝图

evaluation_schema = EvaluationSchema()
evaluations_schema = EvaluationSchema(many=True)
category_schema = EvaluationCategorySchema()
categories_schema = EvaluationCategorySchema(many=True)

# --- 评价消息管理 API ---




@evaluations_bp.get('/<int:eid>')
@jwt_required()
def get_evaluation_thread(eid):
    # 使用 selectinload 预加载所有层级的 replies
    evaluation = Evaluation.query.options(
        selectinload(Evaluation.replies).selectinload(Evaluation.replies)
    ).filter_by(id=eid, is_deleted=False).first_or_404("评价不存在")
    return success(evaluation_schema.dump(evaluation))


@evaluations_bp.post('/<int:eid>/reply')
@admin_required
def reply_to_evaluation(eid: int):
    uid = str(get_jwt_identity() or "")
    try:
        data = EvaluationCreateSchema().load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    parent_eval = Evaluation.query.filter_by(id=eid, is_deleted=False).first_or_404("要回复的评价不存在")

    reply = Evaluation(
        content=data['content'],
        parent_id=parent_eval.id,
        admin_id=uid,
    )
    db.session.add(reply)
    db.session.commit()
    return success(evaluation_schema.dump(reply))


@evaluations_bp.delete('/<int:eid>')
@admin_required
def delete_evaluation(eid: int):
    evaluation = Evaluation.query.filter_by(id=eid, is_deleted=False).first_or_404("评价不存在")
    evaluation.soft_delete()
    db.session.commit()
    return success(None, "删除成功")
@evaluations_bp.get('/categories/list')
@admin_required
def list_categories_paginated():
    page, size = get_pagination()
    kw = (request.args.get('kw') or '').strip()

    q = EvaluationCategory.query.filter_by(is_deleted=False)

    if kw:
        q = q.filter(EvaluationCategory.name.ilike(f'%{kw}%'))

    p = q.order_by(EvaluationCategory.created_at.desc()).paginate(page=page, per_page=size, error_out=False)

    data = page_result(p, categories_schema.dump(p.items))

    return success(data)


# --- 评价类别管理 API ---

@evaluations_bp.get('/categories')
@jwt_required()
def list_categories():
    categories = EvaluationCategory.query.filter_by(is_deleted=False).order_by(
        EvaluationCategory.created_at.desc()).all()
    return success(categories_schema.dump(categories))


@evaluations_bp.post('/categories')
@admin_required
def create_category():
    try:
        data = category_schema.load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    if EvaluationCategory.query.filter_by(name=data['name'], is_deleted=False).first():
        return fail(ApiCodes.CONFLICT, "该类别名称已存在")

    category = EvaluationCategory(name=data['name'])
    db.session.add(category)
    db.session.commit()
    return success(category_schema.dump(category))


@evaluations_bp.put('/categories/<int:cid>')
@admin_required
def update_category(cid: int):
    try:
        data = category_schema.load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    category = EvaluationCategory.query.filter_by(id=cid, is_deleted=False).first_or_404('类别不存在')

    if EvaluationCategory.query.filter(EvaluationCategory.name == data['name'], EvaluationCategory.id != cid,
                                       EvaluationCategory.is_deleted == False).first():
        return fail(ApiCodes.CONFLICT, "该类别名称已存在")

    category.name = data['name']
    db.session.commit()
    return success(category_schema.dump(category))


@evaluations_bp.delete('/categories/<int:cid>')
@admin_required
def delete_category(cid: int):
    category = EvaluationCategory.query.filter_by(id=cid, is_deleted=False).first_or_404('类别不存在')
    category.soft_delete()
    db.session.commit()
    return success(None, "删除成功")


@evaluations_bp.get('')
@admin_required
def list_evaluations():
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)
    page, size = get_pagination()

    school_id = request.args.get('school_id')
    category_id = request.args.get('category_id')
    # 只查询顶层评价 (parent_id 为 None)
    q = Evaluation.query.filter(Evaluation.parent_id.is_(None), Evaluation.is_deleted == False)
    q = q.options(
        joinedload(Evaluation.student).load_only(Student.name),
        joinedload(Evaluation.category).load_only(EvaluationCategory.name),
        joinedload(Evaluation.school).load_only(School.name)  # <-- 新增: 预加载学校信息
    )

    if not is_super:
        managed_school_ids = [m.school_id for m in AdminSchoolMap.query.filter_by(admin_id=uid, is_deleted=False).all()]
        if school_id and school_id not in managed_school_ids:
            return fail(ApiCodes.FORBIDDEN, "无权访问该学校的评价")
        q = q.filter(Evaluation.school_id.in_(managed_school_ids))

    if school_id:
        q = q.filter(Evaluation.school_id == school_id)
    if category_id:
        q = q.filter(Evaluation.category_id == category_id)

    p = q.order_by(Evaluation.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    data = page_result(p, evaluations_schema.dump(p.items))

    return success(data)


@evaluations_bp.get('/my-evaluations')
@jwt_required()
def list_my_evaluations():
    uid = str(get_jwt_identity() or "")
    page, size = get_pagination()
    category_id = request.args.get('category_id')
    kw = request.args.get('kw')
    # 只查询顶层评价 (parent_id 为 None)
    q = Evaluation.query.filter(Evaluation.parent_id.is_(None), Evaluation.is_deleted == False,Evaluation.student_id == uid)
    q = q.options(
        joinedload(Evaluation.student).load_only(Student.name),
        joinedload(Evaluation.category).load_only(EvaluationCategory.name),
        joinedload(Evaluation.school).load_only(School.name)  # <-- 新增: 预加载学校信息
    )
    if category_id:
        q = q.filter(Evaluation.category_id == category_id)
   
    p = q.order_by(Evaluation.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    data = page_result(p, evaluations_schema.dump(p.items))

    return success(data)

@evaluations_bp.post('')
@jwt_required()
def create_evaluation_by_student():
    """
    学生发布一条新的顶层评价。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    try:
        data = StudentEvaluationCreateSchema().load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    # 检查评价类别是否存在
    if not EvaluationCategory.query.filter_by(id=data['category_id'], is_deleted=False).first():
        return fail(ApiCodes.NOT_FOUND, "选择的评价类别不存在")

    new_evaluation = Evaluation(
        content=data['content'],
        category_id=data['category_id'],
        student_id=student.id,
        school_id=student.school_id,
        parent_id=None  # 顶层评价没有 parent_id
    )
    db.session.add(new_evaluation)
    db.session.commit()
    return success(evaluation_schema.dump(new_evaluation), "评价提交成功")


@evaluations_bp.post('/<int:eid>/student-reply')
@jwt_required()
def reply_to_evaluation_by_student(eid: int):
    """
    学生回复一条已有的评价或回复。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    try:
        data = EvaluationCreateSchema().load(request.json) # 复用管理员的回复 Schema
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    parent_eval = Evaluation.query.filter_by(id=eid, is_deleted=False).first_or_404("要回复的评价不存在")

    # 学生只能回复自己学校的评价
    if parent_eval.school_id != student.school_id:
        return fail(ApiCodes.FORBIDDEN, "无权回复该评价")

    reply = Evaluation(
        content=data['content'],
        parent_id=parent_eval.id,
        student_id=student.id,
        admin_id=None # 学生回复时 admin_id 为空
    )
    db.session.add(reply)
    db.session.commit()
    return success(evaluation_schema.dump(reply), "回复成功")
