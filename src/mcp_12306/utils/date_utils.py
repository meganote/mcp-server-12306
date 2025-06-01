"""日期工具"""

from datetime import datetime, date
from typing import Union, Optional
import re


def format_date(dt: Union[datetime, date, str]) -> str:
    """格式化日期为YYYY-MM-DD格式"""
    if isinstance(dt, str):
        # 尝试解析字符串日期
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d").date()
        except ValueError:
            try:
                dt = datetime.strptime(dt, "%Y/%m/%d").date()
            except ValueError:
                raise ValueError(f"无法解析日期格式: {dt}")
    elif isinstance(dt, datetime):
        dt = dt.date()
        
    return dt.strftime("%Y-%m-%d")


def validate_date(date_str: str) -> bool:
    """验证日期格式"""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
        
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_today() -> str:
    """获取今天的日期"""
    return datetime.now().strftime("%Y-%m-%d")


def get_tomorrow() -> str:
    """获取明天的日期"""
    from datetime import timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")