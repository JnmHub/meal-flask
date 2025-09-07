from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from sqlalchemy import MetaData

# 1. 定义命名规范
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# 2. 创建一个带有命名规范的 MetaData 实例
metadata = MetaData(naming_convention=naming_convention)

# 3. 将 metadata 实例传递给 SQLAlchemy 构造函数
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
jwt = JWTManager()
