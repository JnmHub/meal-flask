from marshmallow import fields, Schema, validate, INCLUDE, EXCLUDE, pre_load, validates, ValidationError

from app.schemas.base import BaseSchema


class AdminSchema(BaseSchema):
    id = fields.Str()
    account = name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="账号长度需在 1~64 个字符之间"),
        error_messages={"required": "账号为必填项", "null": "账号不能为空"}
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="姓名长度需在 1~64 个字符之间"),
        error_messages={"required": "姓名为必填项", "null": "姓名不能为空"}
    )
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    school_ids = fields.List(
        fields.Str(),
        required=True,
        validate=[
            validate.Length(min=1, error="至少选择 1 所学校"),
        ],
    )
class AdminShowSchema(BaseSchema):
    id = fields.Str()
    account = name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="账号长度需在 1~64 个字符之间"),
        error_messages={"required": "账号为必填项", "null": "账号不能为空"}
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="姓名长度需在 1~64 个字符之间"),
        error_messages={"required": "姓名为必填项", "null": "姓名不能为空"}
    )
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    school_ids = fields.Method("get_school_ids")

    def get_school_ids(self, obj):
        # 走中间表，过滤软删
        if obj:
            return [m.school_id for m in getattr(obj, "school_maps", []) if not m.is_deleted]
        return None


class AdminUpdateSchema(BaseSchema):
    id = fields.Str()
    account  = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="账号长度需在 1~64 个字符之间"),
        error_messages={"required": "账号为必填项", "null": "账号不能为空"}
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="姓名长度需在 1~64 个字符之间"),
        error_messages={"required": "姓名为必填项", "null": "姓名不能为空"}
    )
    password = fields.Str(
        required=False,
        allow_none=True,  # 允许 null
        load_only=True
    )
    school_ids = fields.List(
        fields.Str(),
        required=True,
        validate=[
            validate.Length(min=1, error="至少选择 1 所学校"),
        ],
    )

    @pre_load
    def drop_blank_password(self, data, **kwargs):
        # 如果 password 是 "" 或 全空格 → 视为未提供，直接丢掉这个键
        if "password" in data:
            val = data["password"]
            if val is None:
                data.pop("password")
            elif isinstance(val, str):
                val = val.strip()
                if val == "":
                    data.pop("password")
                else:
                    data["password"] = val  # 顺便去掉首尾空格
        return data

    @validates("password")
    def validate_password(self, value):
        # 能走到这里，说明 password 存在且非空
        if not (6 <= len(value) <= 15):
            raise ValidationError("密码长度需在 6-15 个字符之间")

