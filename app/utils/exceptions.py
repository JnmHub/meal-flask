from werkzeug.exceptions import HTTPException

class BizError(HTTPException):
    code = 400
    description = '业务异常'

    def __init__(self, description=None, code=None):
        super().__init__(description or self.description)
        if code is not None:
            self.code = code
