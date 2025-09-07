import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, g, Response
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity, get_jwt, create_access_token
from werkzeug.exceptions import NotFound

from app.config import get_config
from app.extensions import db, migrate, jwt
from app.blueprints import auth_bp, students_bp, admins_bp, schools_bp, evaluations_bp, profile_bp
from app.utils.responses import fail, ApiCodes
from app.utils.exceptions import BizError
from app.cli import register_cli

load_dotenv()
def _looks_like_wrapped(obj: object) -> bool:
    return isinstance(obj, dict) and  'success' in obj and 'code' in obj and 'msg' in obj and 'data' in obj

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    CORS(app, expose_headers=['X-Refreshed-Token'])
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(admins_bp)
    app.register_blueprint(schools_bp)
    app.register_blueprint(evaluations_bp)
    app.register_blueprint(profile_bp)

    @app.after_request
    def refresh_expiring_jwt(response):
        """
        在每个请求后检查 JWT 是否即将过期，如果是则刷新它。
        """
        try:
            # 获取当前 token 的过期时间戳 (exp)
            exp_timestamp = get_jwt()["exp"]
            now = datetime.now(timezone.utc)
            target_timestamp = datetime.timestamp(now + app.config['JWT_REFRESH_IF_EXPIRES_IN'])

            # 如果 token 的过期时间在我们的“刷新窗口”内
            if target_timestamp > exp_timestamp:
                # 生成一个新的 access_token
                identity = get_jwt_identity()
                # 重新调用 /auth/refresh 接口的逻辑来获取新的 claims
                # (这里为了简化，我们只保留了最核心的 identity)
                # 在实际复杂业务中，您可能需要重新查询用户以获取完整的 claims
                claims = get_jwt()
                # 过滤掉旧的过期时间等信息
                claims_to_keep = {k: v for k, v in claims.items() if k not in ['exp', 'iat', 'nbf', 'jti']}

                new_token = create_access_token(identity=identity, additional_claims=claims_to_keep)
                # 将新 token 放入响应头中
                response.headers.set('X-Refreshed-Token', new_token)

            return response
        except (RuntimeError, KeyError):
            # 异常处理：
            # RuntimeError: 在请求上下文之外，或者请求的接口不需要认证 (没有有效的JWT)
            # KeyError: 'exp' 字段不存在 (例如在一个 refresh_token 中)
            # 对于这些情况，我们直接返回原始响应，不做任何处理
            return response


    @app.get("/ping")
    def ping():
        return {"pong": True}

    @app.errorhandler(BizError)
    def handle_biz_error(e: BizError):
        return fail(ApiCodes.BAD_REQUEST, str(e))

    @app.errorhandler(404)
    def handle_404(e):
        # 如果是默认提示，就换成中文
        msg = e.description
        if msg == NotFound.description:
            msg = "接口不存在"
        return fail(ApiCodes.NOT_FOUND, msg)

    # @app.errorhandler(Exception)
    # def handle_any(e: Exception):
    #     return fail(ApiCodes.SERVER_ERROR, f"服务器错误: {e!s}")

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
