"""车票数据模型"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field


class TicketQuery(BaseModel):
    """车票查询请求"""
    from_station: str = Field(..., description="出发站")
    to_station: str = Field(..., description="到达站")
    train_date: str = Field(..., description="出发日期 (YYYY-MM-DD)")
    purpose_codes: str = Field(default="ADULT", description="乘客类型")


class Ticket(BaseModel):
    """车票信息模型"""
    train_no: str = Field(..., description="车次")
    from_station_name: str = Field(..., description="出发站名")
    to_station_name: str = Field(..., description="到达站名")
    start_time: str = Field(..., description="出发时间")
    arrive_time: str = Field(..., description="到达时间")
    duration: str = Field(..., description="历时")
    can_web_buy: str = Field(..., description="是否可购买")
    
    # 座位信息
    business_seat_price: Optional[str] = Field(None, description="商务座价格")
    first_class_price: Optional[str] = Field(None, description="一等座价格")
    second_class_price: Optional[str] = Field(None, description="二等座价格")
    soft_sleeper_price: Optional[str] = Field(None, description="软卧价格")
    hard_sleeper_price: Optional[str] = Field(None, description="硬卧价格")
    soft_seat_price: Optional[str] = Field(None, description="软座价格")
    hard_seat_price: Optional[str] = Field(None, description="硬座价格")
    no_seat_price: Optional[str] = Field(None, description="无座价格")
    
    # 余票信息
    business_seat_num: Optional[str] = Field(None, description="商务座余票")
    first_class_num: Optional[str] = Field(None, description="一等座余票")
    second_class_num: Optional[str] = Field(None, description="二等座余票")
    soft_sleeper_num: Optional[str] = Field(None, description="软卧余票")
    hard_sleeper_num: Optional[str] = Field(None, description="硬卧余票")
    soft_seat_num: Optional[str] = Field(None, description="软座余票")
    hard_seat_num: Optional[str] = Field(None, description="硬座余票")
    no_seat_num: Optional[str] = Field(None, description="无座余票")


class TicketSearchResult(BaseModel):
    """车票搜索结果"""
    tickets: List[Ticket] = Field(default_factory=list, description="车票列表")
    query_info: TicketQuery = Field(..., description="查询信息")
    search_date: datetime = Field(default_factory=datetime.now, description="查询时间")
    total: int = Field(0, description="结果总数")