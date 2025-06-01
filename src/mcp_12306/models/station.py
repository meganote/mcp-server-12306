"""车站数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Station(BaseModel):
    """车站信息模型"""
    name: str = Field(..., description="车站名称")
    code: str = Field(..., description="车站代码")
    pinyin: str = Field(..., description="拼音")
    py_short: str = Field(..., description="拼音简写")
    num: str = Field(..., description="车站编号")
    city: Optional[str] = Field(None, description="所属城市")


class StationSearchResult(BaseModel):
    """车站搜索结果"""
    stations: List[Station] = Field(default_factory=list, description="车站列表")
    total: int = Field(0, description="总数量")
    query: str = Field("", description="查询关键词")