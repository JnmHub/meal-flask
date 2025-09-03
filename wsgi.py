from app import create_app
app = create_app()
# 生产: gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
