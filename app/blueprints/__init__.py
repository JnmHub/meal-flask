from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
students_bp = Blueprint('students', __name__, url_prefix='/students')
admins_bp = Blueprint('admins', __name__, url_prefix='/admins')
schools_bp = Blueprint('schools', __name__, url_prefix='/schools')  # ✅ 新增
evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/evaluations')
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

# 触发各路由文件的装饰器执行
from . import auth    # noqa: E402,F401
from . import students  # noqa: E402,F401
from . import admins    # noqa: E402,F401
from . import schools   # ✅ 新增
from . import evaluations # ✅ 新增
from . import profile # ✅ 新增