# app/schemas/school.py
from marshmallow import Schema, fields, validate, EXCLUDE, pre_load

from app.schemas.base import BaseSchema


# 输出 Schema（响应用）
class SchoolOutSchema(BaseSchema):
    id = fields.Str(dump_only=True)
    name = fields.Str()
    alias = fields.Str()  # 英文缩写
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# 创建时的输入 Schema（请求体校验）
class SchoolCreateSchema(BaseSchema):
    class Meta:
        unknown = EXCLUDE  # 忽略多余字段

    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="学校名称长度需在 1~64 个字符之间"),
        error_messages={"required": "学校名称为必填项", "null": "学校名称不能为空"}
    )

    # 别名：英文缩写（2~16 位，字母开头，允许字母数字）
    alias = fields.Str(
        required=True,
        validate=validate.Regexp(
            r"^[A-Za-z][A-Za-z0-9]{1,15}$",
            error="别名必须为英文缩写（2~16 位，字母开头，仅字母数字）"
        ),
        error_messages={"required": "别名为必填项", "null": "别名不能为空"}
    )



# 更新时的输入 Schema（部分字段可选）
class SchoolUpdateSchema(BaseSchema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        validate=validate.Length(min=1, max=64, error="学校名称长度需在 1~64 个字符之间")
    )
    alias = fields.Str(
        validate=validate.Regexp(
            r"^[A-Za-z][A-Za-z0-9]{1,15}$",
            error="别名必须为英文缩写（2~16 位，字母开头，仅字母数字）"
        )
    )


