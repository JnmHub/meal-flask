# app/models/school.py
from uuid import uuid4
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

class School(db.Model):
    __tablename__ = "schools"

    # 主键 UUID（字符串存储，更通用）
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # 学校名称
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # 别名（英文缩写）
    alias: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)

    # 时间戳 + 软删（独立写，避免与 BaseModel 的 int 主键冲突）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    students = relationship("Student", back_populates="school", cascade="all, delete-orphan")
    def soft_delete(self):
        self.is_deleted = True
