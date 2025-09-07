# app/models/evaluation.py
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


# --- 评价类别 ---
class EvaluationCategory(BaseModel):
    __tablename__ = 'evaluation_categories'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="类别名称")

    evaluations = relationship("Evaluation", back_populates="category")


# --- 评价与回复 ---
class Evaluation(BaseModel):
    __tablename__ = 'evaluations'

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评价或回复内容")

    # --- 关联外键 ---
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("evaluation_categories.id"), nullable=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)

    # 回复的管理员，学生发的顶层评价此字段为空
    admin_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("admins.id"), nullable=True, index=True)

    # --- 树形结构 ---
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id"), nullable=True, index=True)

    # --- 关系定义 ---
    school = relationship("School")
    category = relationship("EvaluationCategory", back_populates="evaluations")
    student = relationship("Student")
    admin = relationship("Admin")

    parent = relationship("Evaluation", remote_side=[id], back_populates="replies")
    replies = relationship("Evaluation", back_populates="parent", cascade="all, delete-orphan")