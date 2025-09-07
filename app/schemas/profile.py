# app/schemas/profile.py
from marshmallow import fields, validate, pre_load, validates_schema, ValidationError
from app.schemas.base import BaseSchema

class ProfileUpdateSchema(BaseSchema):
    # 通用姓名/昵称字段
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=64, error="名称长度需在1-64个字符之间"),
        error_messages={"required": "名称不能为空"}
    )
    # ✨ 新增: 当前密码字段
    current_password = fields.Str(
        required=False,
        load_only=True
    )
    # 新密码字段
    password = fields.Str(
        required=False,
        allow_none=True,
        load_only=True
    )

    @pre_load
    def preprocess_password(self, data, **kwargs):
        """在验证前处理密码字段，如果为空字符串则移除。"""
        for field in ['password', 'current_password']:
            if field in data:
                if data[field] is None or not data[field].strip():
                    del data[field]
        return data

    # ✨ 新增: 跨字段验证
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """如果提供了新密码，则当前密码也必须提供。"""
        if 'password' in data and 'current_password' not in data:
            raise ValidationError("如需修改密码，必须提供当前密码。", "current_password")