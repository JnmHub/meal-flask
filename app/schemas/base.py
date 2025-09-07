# app/schemas/base.py
from marshmallow import Schema, EXCLUDE


class BaseSchema(Schema):
    class Meta:
        # 统一所有 DateTime 字段的输出格式
        datetimeformat = "%Y-%m-%d %H:%M:%S"

        unknown = EXCLUDE
