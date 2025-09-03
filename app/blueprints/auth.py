from flask import request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app.blueprints import auth_bp
from app.utils.responses import success, fail, ApiCodes
from app.models.student import Student
from app.models.admin import Admin
from app.extensions import db
from app.utils.security import verify_password, ROLE_ADMIN, ROLE_STUDENT, ROLE_SUPERADMIN, is_super_id


@auth_bp.post('/login')
def login():
    json = request.get_json(silent=True) or {}
    account = (json.get('username') or json.get('account') or '').strip()
    password = json.get('password') or ''
    # 兼容前端两种写法：userType / type
    user_type = (json.get('userType') or json.get('type') or 'student').lower()

    if not account or not password:
        return fail(ApiCodes.BAD_REQUEST, '用户名或密码不能为空')

    if user_type == 'student':
        user_obj = Student.query.filter_by(account=account, is_deleted=False).first()
        if not user_obj or not verify_password(password, user_obj.password_hash):
            return fail(ApiCodes.UNAUTHORIZED, '用户名或密码错误')

        uid = str(user_obj.id)  # ✅ identity 要求字符串
        role = ROLE_STUDENT
        claims = {
            'uid': uid,
            'type': 'student',
            'role': role,
            'account': user_obj.account,
            'nickname': user_obj.nickname
        }
        user_view = {
            'id': uid,
            'account': user_obj.account,
            'name': user_obj.nickname
        }

    elif user_type == 'admin':
        user_obj = Admin.query.filter_by(account=account, is_deleted=False).first()
        if not user_obj or not verify_password(password, user_obj.password_hash):
            return fail(ApiCodes.UNAUTHORIZED, '用户名或密码错误')

        # ✅ 超管判断：id 可能是字符串 SUPER；统一转字符串再比较
        uid = str(user_obj.id)
        role = ROLE_SUPERADMIN if is_super_id(uid) else ROLE_ADMIN

        claims = {
            'uid': uid,
            'type': 'admin',
            'role': role,
            'account': user_obj.account,
            'name': user_obj.display_name
        }
        user_view = {
            'id': uid,
            'account': user_obj.account,
            'name': user_obj.display_name
        }

    else:
        return fail(ApiCodes.BAD_REQUEST, '不支持的登录类型')

    # ✅ identity 仅放字符串 uid；其他都放到 additional_claims
    access = create_access_token(identity=uid, additional_claims=claims)
    # refresh 一般只需要带上最小必要信息；这里仅带 type
    refresh = create_refresh_token(identity=uid, additional_claims={'type': claims['type']})

    return success({
        'access_token': access,
        'refresh_token': refresh,
        'role': role,
        'user': user_view
    })


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh_token():
    # 现在 identity 是字符串 uid
    uid = str(get_jwt_identity())
    j = get_jwt()  # 拿到 refresh 里携带的 claims（我们只放了 type）
    user_type = j.get('type', 'student')

    # 重新判定角色，避免期间权限变化
    if user_type == 'admin':
        admin = Admin.query.get(uid)
        role = ROLE_SUPERADMIN if (admin and is_super_id(admin.id)) else ROLE_ADMIN

        claims = {
            'uid': uid,
            'type': 'admin',
            'role': role,
            'account': admin.username if admin else None,
            'name': admin.display_name if admin else None
        }
    else:
        stu = Student.query.get(uid)
        role = ROLE_STUDENT
        claims = {
            'uid': uid,
            'type': 'student',
            'role': role,
            'account': stu.username if stu else None,
            'nickname': stu.nickname if stu else None
        }

    access = create_access_token(identity=uid, additional_claims=claims)
    return success({'access_token': access, 'role': role})


@auth_bp.get('/me')
@jwt_required()
def me():
    uid = str(get_jwt_identity())
    j = get_jwt()
    # 过滤掉标准保留字段，只回传自定义 claims
    reserved = {'exp', 'iat', 'nbf', 'jti', 'type'}
    ext = {k: v for k, v in j.items() if k not in reserved}
    return success({'identity': {'uid': uid, **ext}})
