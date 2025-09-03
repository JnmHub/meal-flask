# app/models/base.py
from datetime import datetime
from sqlalchemy import DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db
from app.utils.tz import now_local

class BaseModel(db.Model):
    __abstract__ = True
    # 带时区，默认上海时区时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_local, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        self.is_deleted = True
