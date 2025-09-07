# app/models/student.py
from datetime import date
from sqlalchemy import String, Boolean, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from .base import BaseModel

class Student(BaseModel):
    __tablename__ = 'students'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="学生姓名")
    student_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="学号")
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # 就餐状态
    is_eating: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否就餐")
    # 就餐请假时间段
    leave_start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="请假开始日期")
    leave_end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="请假结束日期")

    # 外键关联到学校
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False, index=True)
    school = relationship("School", back_populates="students")

    @property
    def account(self):
        """学生登录账号（由学校英文缩写+学号构成）"""
        if self.school:
            return f"{self.school.alias}{self.student_number}"
        return self.student_number