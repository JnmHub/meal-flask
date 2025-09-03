from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = 'admins'
    # 关键：使用字符串作为主键，支持 id == 'SUPER' 视为超级管理员
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    account: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
