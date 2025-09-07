# app/schemas/evaluation.py
from marshmallow import fields, validate
from app.schemas.base import BaseSchema
from app.schemas.school import SchoolOutSchema
from app.schemas.student import StudentSchema
from app.schemas.admin import AdminSchema


# --- 评价类别 Schema ---
class EvaluationCategorySchema(BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="类别名称长度需在1-64个字符之间"),
        error_messages={"required": "类别名称不能为空"}
    )
    created_at = fields.DateTime(dump_only=True)


# --- 评价与回复 Schema ---
class EvaluationSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    content = fields.Str()
    created_at = fields.DateTime(dump_only=True)

    # 嵌套显示关联信息
    school = fields.Nested(SchoolOutSchema, only=("id", "name"))
    category = fields.Nested(EvaluationCategorySchema, only=("id", "name"))
    student = fields.Nested(StudentSchema, only=("id", "name"))
    admin = fields.Nested(AdminSchema, only=("id", "display_name"))

    # 递归嵌套，用于显示树形结构的回复
    replies = fields.List(fields.Nested('self'))


class EvaluationCreateSchema(BaseSchema):
    content = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="回复内容不能为空"),
        error_messages={"required": "回复内容不能为空"}
    )

class StudentEvaluationCreateSchema(BaseSchema):
    content = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="评价内容不能为空"),
        error_messages={"required": "评价内容不能为空"}
    )
    category_id = fields.Int(
        required=True,
        error_messages={"required": "必须选择一个评价类别"}
    )