# app/models/admin_school_map.py
from uuid import uuid4
from sqlalchemy import String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class AdminSchoolMap(BaseModel):
    __tablename__ = "admin_school_map"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    admin_id: Mapped[str] = mapped_column(String(64), ForeignKey("admins.id"), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("admin_id", "school_id", name="uq_admin_school"),)

    # 可选关系（便于联表取名）
    admin = relationship("Admin", backref="school_maps")
    school = relationship("School", backref="admin_maps")
