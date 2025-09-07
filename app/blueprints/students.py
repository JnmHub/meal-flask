# app/blueprints/students.py
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func, case, or_, and_
from sqlalchemy.orm import joinedload
from marshmallow import ValidationError

from app.blueprints import students_bp
from app.models import AdminSchoolMap
from app.utils.responses import success, fail, ApiCodes
from app.utils.pagination import get_pagination, page_result
from app.models.student import Student
from app.schemas.student import StudentSchema, StudentCreateSchema, StudentUpdateSchema, StudentLeaveSchema
from app.extensions import db
from app.utils.security import hash_password, is_super_id
from app.blueprints.admins import admin_required
from app.utils.tz import now_local

student_schema = StudentSchema()
students_schema = StudentSchema(many=True)


# app/blueprints/students.py

# ... (其他 import 保持不变)
from datetime import datetime
from flask import request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_
# ...

@students_bp.get('')
@admin_required
def list_students():
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)
    page, size = get_pagination()
    school_id = request.args.get('school_id')
    kw = (request.args.get('kw') or '').strip()
    date_str = request.args.get('date')
    # 从 request.args 中获取 is_eating 字符串
    is_eating_str = request.args.get('is_eating')

    q = Student.query.options(joinedload(Student.school)).filter(Student.is_deleted == False)

    # --- 权限和基本筛选 ---
    if not is_super:
        managed_school_ids = [m.school_id for m in AdminSchoolMap.query.filter_by(admin_id=uid, is_deleted=False).all()]
        if school_id and school_id not in managed_school_ids:
            return fail(ApiCodes.FORBIDDEN, "无权访问该学校")
        q = q.filter(Student.school_id.in_(managed_school_ids))

    if school_id:
        q = q.filter(Student.school_id == school_id)

    if kw:
        q = q.filter(or_(Student.name.ilike(f'%{kw}%'), Student.student_number.ilike(f'%{kw}%')))

    # --- 日期筛选（筛选在指定日期正在请假的学生） ---
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # 筛选条件: 该日期在学生的请假开始和结束日期之间
            q = q.filter(and_(
                Student.leave_start_date.isnot(None),
                Student.leave_end_date.isnot(None),
                Student.leave_start_date <= target_date,
                Student.leave_end_date >= target_date
            ))
        except ValueError:
            return fail(ApiCodes.BAD_REQUEST, "日期格式不正确，请使用 YYYY-MM-DD 格式")

    # --- 就餐状态筛选 (正确处理布尔值) ---
    if is_eating_str is not None:
        # 将 "true" (不区分大小写) 转为 True, 其他 (如 "false") 转为 False
        is_eating_bool = is_eating_str.lower() == 'true'
        q = q.filter(Student.is_eating == is_eating_bool)

    # --- 分页和返回 ---
    p = q.order_by(Student.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    data = page_result(p, students_schema.dump(p.items))
    return success(data)


# ✨ 新增：统计API
@students_bp.get('/stats')
@admin_required
def get_student_stats():
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)

    date_str = request.args.get('date')
    school_id = request.args.get('school_id')

    if not date_str:
        return fail(ApiCodes.BAD_REQUEST, "必须提供 日期 参数")

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return fail(ApiCodes.BAD_REQUEST, "日期格式不正确，请使用 YYYY-MM-DD 格式")

    q = db.session.query(Student.id).filter(Student.is_deleted == False)

    # 权限控制
    if not is_super:
        managed_school_ids = [m.school_id for m in AdminSchoolMap.query.filter_by(admin_id=uid, is_deleted=False).all()]
        if school_id and school_id not in managed_school_ids:
            return fail(ApiCodes.FORBIDDEN, "无权访问该学校的统计数据")
        q = q.filter(Student.school_id.in_(managed_school_ids))

    if school_id:
        q = q.filter(Student.school_id == school_id)

    # 定义学生当天是否在请假
    is_on_leave = and_(
        Student.leave_start_date.isnot(None),
        Student.leave_end_date.isnot(None),
        Student.leave_start_date <= target_date,
        Student.leave_end_date >= target_date
    )

    # 不就餐的条件：is_eating 为 False，或者当天在请假期间
    is_not_eating_condition = or_(
        Student.is_eating == False,
        is_on_leave
    )

    # 使用 case 语句进行条件计数
    stats_query = q.with_entities(
        func.count(Student.id).label("total_students"),
        func.sum(case((is_not_eating_condition, 1), else_=0)).label("not_eating_count"),
        func.sum(case((~is_not_eating_condition, 1), else_=0)).label("eating_count")
    )

    result = stats_query.one()

    return success({
        "total_students": result.total_students or 0,
        "eating_count": result.eating_count or 0,
        "not_eating_count": result.not_eating_count or 0,
    })


@students_bp.post('')
@admin_required
def create_student():
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)

    try:
        data = StudentCreateSchema().load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    school_id = data['school_id']
    if not is_super:
        # 检查管理员是否有权操作此学校
        if not AdminSchoolMap.query.filter_by(admin_id=uid, school_id=school_id, is_deleted=False).first():
            return fail(ApiCodes.FORBIDDEN, "无权在该学校下创建学生")

    # 检查学号是否已存在
    if Student.query.filter_by(school_id=school_id, student_number=data['student_number'], is_deleted=False).first():
        return fail(ApiCodes.CONFLICT, "该学校下学号已存在")

    s = Student(
        name=data['name'],
        student_number=data['student_number'],
        school_id=school_id,
        is_eating=data['is_eating']
    )
    if 'password' in data and data['password']:
        s.password_hash = hash_password(data['password'])

    db.session.add(s)
    db.session.commit()
    return success(student_schema.dump(s))


@students_bp.put('/<int:sid>')
@admin_required
def update_student(sid: int):
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)

    try:
        data = StudentUpdateSchema().load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    s = Student.query.filter_by(id=sid, is_deleted=False).first()
    if not s:
        return fail(ApiCodes.NOT_FOUND, "学生不存在")

    if not is_super:
        if not AdminSchoolMap.query.filter_by(admin_id=uid, school_id=s.school_id, is_deleted=False).first():
            return fail(ApiCodes.FORBIDDEN, "无权修改该学生信息")

    # 更新字段
    for key, value in data.items():
        if key == 'password':
            if value:
                s.password_hash = hash_password(value)
            else:
                s.password_hash = None  # 允许设置为空密码
        else:
            setattr(s, key, value)

    db.session.commit()
    return success(student_schema.dump(s))


@students_bp.delete('/<int:sid>')
@admin_required
def remove_student(sid: int):
    uid = str(get_jwt_identity() or "")
    is_super = is_super_id(uid)

    s = Student.query.get_or_404(sid)
    if not is_super:
        if not AdminSchoolMap.query.filter_by(admin_id=uid, school_id=s.school_id, is_deleted=False).first():
            return fail(ApiCodes.FORBIDDEN, "无权删除该学生")

    s.soft_delete()
    db.session.commit()
    return success({'id': sid}, '已删除')


@students_bp.get('/me/status')
@jwt_required()
def get_my_eating_status():
    """
    获取当前登录学生今天的就餐状态。
    综合 is_eating 字段和请假时间段进行判断。
    如果因请假而不就餐，则返回请假时间段。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    today = now_local().date()
    is_on_leave = False

    # 检查今天是否在请假期间
    if student.leave_start_date and student.leave_end_date:
        if student.leave_start_date <= today <= student.leave_end_date:
            is_on_leave = True

    # 最终就餐状态：is_eating 必须为 True 且 今天不在请假期间
    final_status = student.is_eating and not is_on_leave

    # ✨ 构造返回数据
    response_data = {
        'is_eating': final_status,
        'reason': {
            'is_on_leave': is_on_leave,
            'eating_setting': student.is_eating
        }
    }

    # ✨ 如果是请假状态，则在返回数据中附上请假日期
    if student.leave_start_date and student.leave_end_date:
        response_data['reason']['leave_start_date'] = student.leave_start_date.isoformat()
        response_data['reason']['leave_end_date'] = student.leave_end_date.isoformat()

    return success(response_data)


@students_bp.put('/me/eating-status')
@jwt_required()
def set_my_eating_status():
    """
    学生设置自己的就餐状态（停餐/就餐申请）。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    json_data = request.get_json(silent=True)
    if json_data is None or 'is_eating' not in json_data or not isinstance(json_data['is_eating'], bool):
        return fail(ApiCodes.BAD_REQUEST, "请求参数错误，需要提供布尔型的 'is_eating' 字段")

    status = json_data['is_eating']
    student.is_eating = status
    db.session.commit()

    return success({'is_eating': status}, "就餐状态已更新")


@students_bp.post('/me/leave')
@jwt_required()
def apply_for_leave():
    """
    学生提交就餐请假申请。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    try:
        data = StudentLeaveSchema().load(request.json)
    except ValidationError as err:
        return fail(ApiCodes.BAD_REQUEST, "参数校验失败", errors=err.messages)

    # 业务逻辑：需提前一天申请
    tomorrow = now_local().date() + timedelta(days=1)

    if data['leave_start_date'] < tomorrow:
        return fail(ApiCodes.BAD_REQUEST, "请假申请必须至少提前一天提交")

    student.leave_start_date = data['leave_start_date']
    student.leave_end_date = data['leave_end_date']
    db.session.commit()

    return success({
        'leave_start_date': student.leave_start_date.isoformat(),
        'leave_end_date': student.leave_end_date.isoformat()
    }, "请假申请成功")


@students_bp.delete('/me/leave')
@jwt_required()
def cancel_leave():
    """
    学生清空（取消）自己的请假时间。
    """
    uid = get_jwt_identity()
    student = Student.query.filter_by(id=uid, is_deleted=False).first_or_404("学生不存在")

    student.leave_start_date = None
    student.leave_end_date = None
    db.session.commit()

    return "请假已取消"