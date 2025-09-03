# Flask 快速开发模板（完全可跑）

## 快速开始
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 初始化数据库（两种方式，选其一）
**方式 A：迁移**（推荐）
```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "init tables"
flask --app wsgi db upgrade
```

**方式 B：直接建表**
```bash
flask --app wsgi init-db
```

### 创建超级管理员（id = SUPER）
```bash
flask --app wsgi create-super
# 按提示输入 username / password
```

### 启动
```bash
python run.py
# 或: flask --app wsgi run --debug
```

## 接口
- 登录 `POST /auth/login`
  - 学生: `{"type":"student","username":"stu1","password":"123456"}`
  - 管理员: `{"type":"admin","username":"root","password":"123456"}`
  - **角色**: admin 登录默认 `role=admin`；若管理员 **id 为 SUPER** 则 `role=superadmin`
- 刷新 `POST /auth/refresh`（用 refresh token）
- 当前身份 `GET /auth/me`（带 Authorization: Bearer ...）
- 学生列表 `GET /students?page=1&size=10`
- 新增学生 `POST /students`
- 管理员列表（仅管理员/超管）`GET /admins`
- 新增管理员（仅超管）`POST /admins`
