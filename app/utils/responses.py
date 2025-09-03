from functools import wraps

from flask import jsonify

class ApiCodes:
    OK = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    SERVER_ERROR = 500

def success(data=None, msg='成功', code=ApiCodes.OK, **extra):
    payload = {'success': True, 'code': code, 'msg': msg, 'data': data}
    if extra: payload.update(extra)
    return jsonify(payload), 200

def fail(code=ApiCodes.BAD_REQUEST, msg='失败', http_status: int | None = None, **extra):
    payload = {'success': False, 'code': code, 'msg': msg, 'data': None}
    if extra: payload.update(extra)
    return jsonify(payload), http_status or 200


def no_wrapper(fn):
    """给视图加上 _no_wrapper 标记；在 before_request 里读这个标记。"""
    setattr(fn, "_no_wrapper", True)
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper