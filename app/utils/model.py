from typing import Any, Dict, Union
from sqlalchemy.orm import Session
from app.extensions import db


def update_model_fields(
        model_instance: Any,
        update_data: Dict[str, Any],
        skip_fields: Union[list, tuple] = None
) -> None:
    """
    通用模型字段更新工具函数

    Args:
        model_instance: 数据库模型实例
        update_data: 包含字段更新信息的字典
        skip_fields: 需要跳过的字段列表（不更新这些字段）
    """
    # 处理空的跳过字段列表
    skip_fields = skip_fields or []

    # 遍历更新数据，设置字段值
    for key, value in update_data.items():
        # 跳过指定字段和不存在的字段
        if key in skip_fields:
            continue

        # 检查模型是否有该字段，避免设置不存在的属性
        if hasattr(model_instance, key):
            setattr(model_instance, key, value)
        else:
            # 可根据需要改为警告日志
            # 例如：logger.warning(f"模型 {model_instance.__class__.__name__} 不存在字段 {key}")
            pass
