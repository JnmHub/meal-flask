# app/blueprints/auth.py
from flask import request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app.blueprints import auth_bp
from app.utils.responses import success, fail, ApiCodes
from app.models.student import Student
from app.models.admin import Admin
# ✨ 新增导入
from app.models.school import School
from app.extensions import db
from app.utils.security import verify_password, ROLE_ADMIN, ROLE_STUDENT, ROLE_SUPERADMIN, is_super_id


@auth_bp.post('/login')
def login():
    json_data = request.get_json(silent=True) or {}
    account = (json_data.get('username') or json_data.get('account') or '').strip()
    password = json_data.get('password') or ''
    user_type = (json_data.get('userType') or json_data.get('type') or 'student').lower()

    if not account:
        return fail(ApiCodes.BAD_REQUEST, '用户名不能为空')

    if user_type == 'student':
        # --- ✨ 学生登录逻辑重构 ---
        schools = School.query.filter_by(is_deleted=False).all()
        user_obj = None

        # 1. 遍历所有学校，匹配别名
        for school in schools:
            if account.startswith(school.alias):
                student_number = account[len(school.alias):]

                # 2. 根据 school_id 和 student_number 查找学生
                user_obj = Student.query.filter_by(
                    school_id=school.id,
                    student_number=student_number,
                    is_deleted=False
                ).first()

                if user_obj:
                    break

        # 3. 验证密码（处理密码为空的情况）
        password_ok = False
        if user_obj:
            # Case 1: 学生密码未设置 (为空)
            if not user_obj.password_hash:
                password_ok = True  # 密码为空时，直接验证通过
            # Case 2: 学生密码已设置，需要验证
            else:
                password_ok = verify_password(password, user_obj.password_hash)

        if not user_obj or not password_ok:
            return fail(ApiCodes.BAD_REQUEST, '用户名或密码错误')
        # --- 登录逻辑重构结束 ---

        uid = str(user_obj.id)
        role = ROLE_STUDENT
        claims = {
            'uid': uid,
            'type': 'student',
            'role': role,
            'account': user_obj.account,  # 使用 account 属性
            'name': user_obj.name
        }
        user_view = {
            'id': uid,
            'account': user_obj.account,
            'name': user_obj.name
        }

    elif user_type == 'admin':
        user_obj = Admin.query.filter_by(account=account, is_deleted=False).first()
        if not user_obj or not verify_password(password, user_obj.password_hash):
            return fail(ApiCodes.BAD_REQUEST, '用户名或密码错误')

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

    access = create_access_token(identity=uid, additional_claims=claims)
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
    uid = str(get_jwt_identity())
    j = get_jwt()
    user_type = j.get('type', 'student')

    if user_type == 'admin':
        admin = Admin.query.get(uid)
        role = ROLE_SUPERADMIN if (admin and is_super_id(admin.id)) else ROLE_ADMIN

        claims = {
            'uid': uid,
            'type': 'admin',
            'role': role,
            'account': admin.account if admin else None,
            'name': admin.display_name if admin else None
        }
    else:
        stu = Student.query.get(uid)
        role = ROLE_STUDENT
        claims = {
            'uid': uid,
            'type': 'student',
            'role': role,
            'account': stu.account if stu else None,
            'name': stu.name if stu else None,
        }

    access = create_access_token(identity=uid, additional_claims=claims)
    return success({'access_token': access, 'role': role})


@auth_bp.get('/me')
@jwt_required()
def me():
    uid = str(get_jwt_identity())
    j = get_jwt()
    reserved = {'exp', 'iat', 'nbf', 'jti', 'type'}
    ext = {k: v for k, v in j.items() if k not in reserved}
    return success({'identity': {'uid': uid, **ext}})