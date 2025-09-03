from flask import request
from flask_jwt_extended import jwt_required
from app.blueprints import students_bp
from app.utils.responses import success, fail, ApiCodes
from app.utils.pagination import get_pagination
from app.models.student import Student
from app.schemas.student import StudentSchema
from app.extensions import db
from app.utils.security import hash_password

student_schema = StudentSchema()
students_schema = StudentSchema(many=True)

@students_bp.get('')
@jwt_required()
def list_students():
    page, size = get_pagination()
    q = Student.query.filter_by(is_deleted=False)
    pagination = q.paginate(page=page, per_page=size, error_out=False)
    return success({
        'total': pagination.total,
        'page': pagination.page,
        'size': pagination.per_page,
        'items': students_schema.dump(pagination.items)
    })

@students_bp.post('')
@jwt_required()
def create_student():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return fail(ApiCodes.BAD_REQUEST, 'username/password 必填')
    if Student.query.filter_by(username=username).first():
        return fail(ApiCodes.CONFLICT, '用户名已存在')
    s = Student(username=username, password_hash=hash_password(password), nickname=data.get('nickname'))
    db.session.add(s)
    db.session.commit()
    return success(student_schema.dump(s))

@students_bp.delete('/<int:sid>')
@jwt_required()
def remove_student(sid: int):
    s = Student.query.get_or_404(sid)
    s.soft_delete()
    db.session.commit()
    return success({'id': sid}, '已删除')
