from marshmallow import fields, Schema

from app.schemas.base import BaseSchema


class StudentSchema(BaseSchema):
    id = fields.Int()
    username = fields.Str()
    nickname = fields.Str(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
