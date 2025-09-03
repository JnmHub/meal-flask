from functools import wraps
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.blueprints import admins_bp
from app.models import AdminSchoolMap
from app.services.admin_school import bind_schools_to_admin, replace_admin_schools, ensure_schools_exist_or_400
from app.utils.model import update_model_fields
from app.utils.pagination import get_pagination, page_result
from app.utils.responses import success, fail, ApiCodes
from app.models.admin import Admin
from app.schemas.admin import AdminSchema, AdminUpdateSchema, AdminShowSchema
from app.extensions import db
from app.utils.security import hash_password, ROLE_ADMIN, ROLE_SUPERADMIN

admin_schema = AdminSchema()
admin_update_schema = AdminUpdateSchema()
admins_show_schema = AdminShowSchema(many=True)
admins_schema = AdminSchema(many=True)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        role = claims.get('role')
        if role not in (ROLE_ADMIN, ROLE_SUPERADMIN):
            return fail(ApiCodes.FORBIDDEN, '需要管理员权限')
        return fn(*args, **kwargs)
    return wrapper

def super_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != ROLE_SUPERADMIN:
            return fail(ApiCodes.FORBIDDEN, '需要超级管理员权限')
        return fn(*args, **kwargs)
    return wrapper

@admins_bp.get('')
@admin_required
def list_admins():
    account = (request.args.get('account') or '').strip()
    name = (request.args.get('display_name') or '').strip()
    page, size = get_pagination()
    q = (Admin.query.filter_by(is_deleted=False)
         .options(selectinload(Admin.school_maps).load_only(
             AdminSchoolMap.school_id, AdminSchoolMap.is_deleted
         ))
         .order_by(Admin.created_at.desc()))
    q = q.filter(
        Admin.account.ilike(f'%{account}%'),
        Admin.display_name.ilike(f'%{name}%'),
    )
    p = q.paginate(page=page, per_page=size, error_out=False)
    data = page_result(p, admins_show_schema.dump(p.items))
    return success(data)

@admins_bp.post('')
@super_required
def create_admin():
    data = request.get_json(silent=True) or {}
    account = (data.get('account') or '').strip()
    password = (data.get('password') or '').strip()

    if not account or not password:
        return fail(ApiCodes.BAD_REQUEST, 'account/password')

    if Admin.query.filter_by(account=account).first():
        return fail(ApiCodes.CONFLICT, 'account 已存在')

    a = Admin(account=account, password_hash=hash_password(password), display_name=data.get('display_name'))
    db.session.add(a)
    db.session.flush()
    if data.get('school_ids'):
        bind_schools_to_admin(a.id, data['school_ids'])
    db.session.commit()
    return success(admin_schema.dump(a))

@admins_bp.put('/<string:aid>')
@super_required
def update_admin(aid: str):
    json_data = request.get_json(silent=True)
    if json_data is None:
        return fail(ApiCodes.BAD_REQUEST, "请求体必须为 JSON（Content-Type: application/json）")
    try:
        data = admin_update_schema.load(json_data)  # ✅ 中文校验提示
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)
    exists = Admin.query.filter(
        Admin.is_deleted.is_(False),
        Admin.account == data['account'],
        Admin.id != aid
    ).first()
    if exists:
        return fail(ApiCodes.CONFLICT, "此账号已存在")
    admin = Admin.query.filter_by(id=aid, is_deleted=False).first()
    try:
        ensure_schools_exist_or_400(data['school_ids'])
    except RuntimeError as e:
        return fail(ApiCodes.BAD_REQUEST, str(e))
    if not admin:
        return fail(ApiCodes.NOT_FOUND, "管理员不存在或已被删除")
    if 'password' in data:
        password = data.pop('password')
        admin.password_hash = hash_password(password)  # 假设存在哈希函数
    update_model_fields(admin, data)
    replace_admin_schools(aid, data['school_ids'])
    db.session.commit()
    return "修改成功"


