from passlib.hash import bcrypt

ROLE_STUDENT = 'student'
ROLE_ADMIN = 'admin'
ROLE_SUPERADMIN = 'superadmin'

def hash_password(raw: str) -> str:
    return bcrypt.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.verify(raw, hashed)

def is_super_id(uid: str | int) -> bool:
    """ID 包含 SUPER 即视为超管（大）。"""
    return "SUPER" in str(uid)
