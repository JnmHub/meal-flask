import os
from datetime import timedelta
ACCESS_HOURS  = int(os.getenv("JWT_ACCESS_HOURS", 6))
REFRESH_DAYS  = int(os.getenv("JWT_REFRESH_DAYS", 7))
class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///./dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=ACCESS_HOURS)  # 访问令牌有效期
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=REFRESH_DAYS)  # 刷新令牌有效期
    JWT_REFRESH_IF_EXPIRES_IN = timedelta(minutes=int(os.getenv("JWT_REFRESH_IF_EXPIRES_IN", 30)))

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class ProductionConfig(BaseConfig):
    DEBUG = False

config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
