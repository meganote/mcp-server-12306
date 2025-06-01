"""查询请求和响应模型"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """MCP查询请求"""
    method: str = Field(..., description="查询方法")
    params: Dict[str, Any] = Field(default_factory=dict, description="查询参数")


class QueryResponse(BaseModel):
    """MCP查询响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: float = Field(..., description="时间戳")