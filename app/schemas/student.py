# app/schemas/student.py
from marshmallow import fields, validate, post_load, ValidationError
from app.schemas.base import BaseSchema
from app.schemas.school import SchoolOutSchema


class StudentSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    student_number = fields.Str()
    account = fields.Str(dump_only=True)
    is_eating = fields.Boolean()
    # ✨ 修正: 明确允许这两个字段在序列化时为空
    leave_start_date = fields.Date(allow_none=True)
    leave_end_date = fields.Date(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    school = fields.Nested(SchoolOutSchema, only=("id", "name", "alias"))


class StudentCreateSchema(BaseSchema):
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="姓名长度需在1-64个字符之间"),
        error_messages={"required": "姓名不能为空", "null": "姓名不能为空"}
    )
    student_number = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="学号长度需在1-64个字符之间"),
        error_messages={"required": "学号不能为空", "null": "学号不能为空"}
    )
    password = fields.Str(
        required=False,
        allow_none=True,
        load_only=True
    )
    school_id = fields.Str(
        required=True,
        error_messages={"required": "必须选择一个学校", "null": "学校不能为空"}
    )
    is_eating = fields.Boolean(missing=True)


class StudentUpdateSchema(BaseSchema):
    name = fields.Str(
        validate=validate.Length(min=1, max=64, error="姓名长度需在1-64个字符之间")
    )
    student_number = fields.Str(
        validate=validate.Length(min=1, max=64, error="学号长度需在1-64个字符之间")
    )
    password = fields.Str(
        required=False,
        allow_none=True,
        load_only=True
    )
    is_eating = fields.Boolean()

    # ✨ 1. 使用 DateTime 字段来接收包含时间的日期字符串
    leave_start_date = fields.Date(
        allow_none=True,
        error_messages={"invalid": "不是有效的日期时间格式"}
    )
    leave_end_date = fields.Date(
        allow_none=True,
        error_messages={"invalid": "不是有效的日期时间格式"}
    )
class StudentLeaveSchema(BaseSchema):
    leave_start_date = fields.Date(
        required=True,
        error_messages={"required": "请假开始日期不能为空"}
    )
    leave_end_date = fields.Date(
        required=True,
        error_messages={"required": "请假结束日期不能为空"}
    )

    @post_load
    def validate_dates(self, data, **kwargs):
        """校验结束日期是否大于等于开始日期"""
        if data['leave_start_date'] > data['leave_end_date']:
            raise ValidationError("请假结束日期不能早于开始日期", "leave_end_date")
        return data

