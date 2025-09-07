# app/blueprints/profile.py
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError

from app.blueprints import profile_bp  # 确保导入正确
from app.models import Student, Admin
from app.schemas.profile import ProfileUpdateSchema
from app.utils.responses import success, fail, ApiCodes
from app.extensions import db
from app.utils.security import hash_password, verify_password  # ✨ 导入 verify_password

profile_update_schema = ProfileUpdateSchema()


@profile_bp.put('')
@jwt_required()
def update_my_profile():
    """
    通用接口，用于所有登录用户修改自己的个人信息。
    修改密码时，必须提供正确的当前密码。
    """
    uid = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get('type')

    try:
        data = profile_update_schema.load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    user_obj = None
    if user_type == 'student':
        user_obj = Student.query.get_or_404(uid)
        user_obj.name = data['name']
    elif user_type == 'admin':
        user_obj = Admin.query.get_or_404(uid)
        user_obj.display_name = data['name']
    else:
        return fail(ApiCodes.BAD_REQUEST, "无效的用户类型")

    # ✨ 如果请求中包含了 'password' 字段，则执行密码更新逻辑
    if 'password' in data:
        current_password = data['current_password']

        # 检查用户是否设置了密码
        if not user_obj.password_hash:
            return fail(ApiCodes.BAD_REQUEST, "您的账户当前未设置密码，无法使用“当前密码”进行验证")

        # 验证当前密码是否正确
        if not verify_password(current_password, user_obj.password_hash):
            return fail(ApiCodes.BAD_REQUEST, "当前密码不正确")

        # 更新为新密码
        user_obj.password_hash = hash_password(data['password'])

    db.session.commit()
    return success(None, "个人信息更新成功")