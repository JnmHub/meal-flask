import json
import os
from dotenv import load_dotenv
from flask import Flask, request, g, Response
from flask_cors import CORS

from app.config import get_config
from app.extensions import db, migrate, jwt
from app.blueprints import auth_bp, students_bp, admins_bp, schools_bp
from app.utils.responses import fail, ApiCodes
from app.utils.exceptions import BizError
from app.cli import register_cli

load_dotenv()
def _looks_like_wrapped(obj: object) -> bool:
    return isinstance(obj, dict) and  'success' in obj and 'code' in obj and 'msg' in obj and 'data' in obj

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(admins_bp)
    app.register_blueprint(schools_bp)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    @app.errorhandler(BizError)
    def handle_biz_error(e: BizError):
        return fail(ApiCodes.BAD_REQUEST, str(e))

    @app.errorhandler(404)
    def handle_404(_):
        return fail(ApiCodes.NOT_FOUND, "接口不存在")

    @app.errorhandler(Exception)
    def handle_any(e: Exception):
        return fail(ApiCodes.SERVER_ERROR, f"服务器错误: {e!s}")

    @app.before_request
    def _mark_no_wrapper():
        """如果视图函数带有 _no_wrapper 标记，则在 g 上做标记。"""
        if request.path.startswith(('/static', '/swagger', '/docs', '/favicon.ico')):
            g.no_wrapper = True
        view = app.view_functions.get(request.endpoint)
        if view and getattr(view, "_no_wrapper", False):
            g.no_wrapper = True

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return fail(ApiCodes.UNAUTHORIZED, f"无效令牌: {reason}")

    @jwt.unauthorized_loader
    def _missing_token(reason):
        return fail(ApiCodes.UNAUTHORIZED, f"未携带令牌: {reason}")

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_data):
        return fail(ApiCodes.UNAUTHORIZED, "令牌已过期")

    @jwt.revoked_token_loader
    def _revoked_token(jwt_header, jwt_data):
        return fail(ApiCodes.UNAUTHORIZED, "令牌已撤销")
    @app.after_request
    def _unify_response(resp: Response):
        # 1) 显式跳过
        if getattr(g, 'no_wrapper', False):
            return resp

        # 2) 文件/流/直通响应跳过（如 send_file）
        if resp.direct_passthrough or resp.is_streamed:
            return resp

        ctype = (resp.mimetype or '').lower()

        # 3) 空响应体：包装成功
        raw_text = resp.get_data(as_text=True) if resp.data is not None else ''
        if (not raw_text) and (ctype in ('', 'text/plain', 'application/octet-stream')):
            # 空则包装为 success
            wrapped = {'success': True, 'code': 0, 'msg': '成功', 'data': None}
            resp.set_data(json.dumps(wrapped, ensure_ascii=False))
            resp.mimetype = 'application/json'
            return resp
        # 4) 已经是 JSON 的处理
        if ctype == 'application/json':
            try:
                obj = json.loads(raw_text) if raw_text else {}
            except Exception:
                # 不是合法 JSON，就别动它
                return resp
            if 'errors' in obj:
                for _, error in obj['errors'].items():
                    obj['msg'] = obj['msg'] + "," + ",".join(error)
                del obj['errors']
                resp.set_data(json.dumps(obj, ensure_ascii=False))
            # 已是统一结构 → 直接返回

            if _looks_like_wrapped(obj):
                return resp

            # 错误页面（如自定义 error handler 返回了状态/消息）
            if isinstance(obj, dict) and 'status' in obj and ('error' in obj or 'message' in obj):
                code = obj.get('status', 400)
                msg = f"{obj.get('error', 'error')}:{obj.get('message', '')}"
                new_body = {'success': False, 'code': code, 'msg': msg, 'data': None}
                resp.set_data(json.dumps(new_body, ensure_ascii=False))
                return resp

            # 正常 JSON → 包成 data
            new_body = {'success': True, 'code': 0, 'msg': '成功', 'data': obj}
            resp.set_data(json.dumps(new_body, ensure_ascii=False))
            return resp

        # 5) 文本 → 包一层并改为 JSON
        # 5) 文本 → 包一层并改为 JSON，但 HTML 保持原样
        if ctype.startswith('text/') and ctype != 'text/csv':
            new_body = {'success': True, 'code': 0, 'msg': '成功', 'data': raw_text}
            resp.set_data(json.dumps(new_body, ensure_ascii=False))
            resp.mimetype = 'application/json'
            return resp

        # 6) 其他类型（比如 html、xml、图片等）默认不动
        return resp
    register_cli(app)
    return app
