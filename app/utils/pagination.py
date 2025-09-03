from flask import request

def get_pagination(default_page=1, default_size=10, max_size=100):
    """
    支持这几种查询参数：
    - page / size
    - current / size
    - current / pageSize   （很多前端表格的命名）
    """
    # 兼容多种别名
    raw_page = request.args.get('page', request.args.get('current', default_page))
    raw_size = request.args.get('size', request.args.get('pageSize', default_size))
    try:
        page = int(raw_page)
        size = int(raw_size)
    except (TypeError, ValueError):
        page, size = default_page, default_size

    size = min(max(size, 1), max_size)
    page = max(page, 1)
    return page, size


def page_result(pagination, records):
    """
    根据 Flask-SQLAlchemy 的 Pagination 对象，组装你要的返回结构。
    pagination: q.paginate(...) 返回的对象
    records: 已序列化后的列表（比如 schema.dump(pagination.items)）
    """
    return {
        "records": records,
        "total": pagination.total,
        "size": pagination.per_page,
        "current": pagination.page,
        "pages": pagination.pages,
    }
