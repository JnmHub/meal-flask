from uuid import uuid4

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db
from .base import BaseModel

class Student(BaseModel):
    __tablename__ = 'students'
    id: Mapped[str] = mapped_column(String(64), primary_key=True,default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
