"""车票查询服务"""

import logging
import urllib.parse
from typing import List, Optional
from datetime import datetime

from ..models.ticket import Ticket, TicketQuery, TicketSearchResult
from .http_client import HttpClient
from .station_service import StationService

logger = logging.getLogger(__name__)


class TicketService:
    """车票查询服务"""
    
    def __init__(self):
        self.http_client = HttpClient()
        self.station_service = StationService()
        
    async def query_tickets(self, query: TicketQuery) -> TicketSearchResult:
        """查询车票"""
        try:
            # 获取车站代码
            from_code = await self.station_service.get_station_code(query.from_station)
            to_code = await self.station_service.get_station_code(query.to_station)
            
            if not from_code or not to_code:
                logger.error(f"无法找到车站代码: {query.from_station} -> {query.to_station}")
                return TicketSearchResult(
                    tickets=[],
                    query_info=query,
                    total=0
                )
                
            # 构建查询URL - 使用硬编码的queryG地址
            url = "https://kyfw.12306.cn/otn/leftTicket/queryG"
            params = {
                'leftTicketDTO.train_date': query.train_date,
                'leftTicketDTO.from_station': from_code,
                'leftTicketDTO.to_station': to_code,
                'purpose_codes': query.purpose_codes
            }
            
            async with self.http_client:
                response = await self.http_client.get(url, params=params)
                data = response.json()
                
                if not data.get('status'):
                    logger.error(f"12306返回错误: {data.get('messages', '未知错误')}")
                    return TicketSearchResult(
                        tickets=[],
                        query_info=query,
                        total=0
                    )
                    
                # 解析车票数据
                tickets = self._parse_tickets(data.get('data', {}).get('result', []))
                
                return TicketSearchResult(
                    tickets=tickets,
                    query_info=query,
                    total=len(tickets)
                )
                
        except Exception as e:
            logger.error(f"查询车票失败: {e}")
            return TicketSearchResult(
                tickets=[],
                query_info=query,
                total=0
            )
            
    def _parse_tickets(self, ticket_data: List[str]) -> List[Ticket]:
        """解析车票数据"""
        tickets = []
        
        for ticket_str in ticket_data:
            try:
                # 12306返回的数据格式是用|分隔的字符串
                parts = ticket_str.split('|')
                
                if len(parts) < 35:  # 确保有足够的字段
                    continue
                    
                ticket = Ticket(
                    train_no=parts[3],  # 车次
                    from_station_name=parts[6],  # 出发站
                    to_station_name=parts[7],  # 到达站
                    start_time=parts[8],  # 出发时间
                    arrive_time=parts[9],  # 到达时间
                    duration=parts[10],  # 历时
                    can_web_buy=parts[11],  # 是否可购买

                    # 票价信息（暂为None，后续可补充真实票价）
                    business_seat_price=None,
                    first_class_price=None,
                    second_class_price=None,
                    soft_sleeper_price=None,
                    hard_sleeper_price=None,
                    soft_seat_price=None,
                    hard_seat_price=None,
                    no_seat_price=None,

                    # 余票信息 - 根据12306实际字段位置调整
                    business_seat_num=parts[32] if parts[32] != '' else None,  # 商务座余票
                    first_class_num=parts[31] if parts[31] != '' else None,   # 一等座余票
                    second_class_num=parts[30] if parts[30] != '' else None,  # 二等座余票
                    soft_sleeper_num=parts[23] if parts[23] != '' else None,  # 软卧余票
                    hard_sleeper_num=parts[28] if parts[28] != '' else None,  # 硬卧余票
                    soft_seat_num=parts[24] if parts[24] != '' else None,     # 软座余票
                    hard_seat_num=parts[29] if parts[29] != '' else None,     # 硬座余票
                    no_seat_num=parts[26] if parts[26] != '' else None,       # 无座余票
                )
                
                tickets.append(ticket)
                
            except (IndexError, ValueError) as e:
                logger.warning(f"解析车票数据失败: {e}")
                continue
                
        return tickets
        
    async def get_ticket_price(self, train_no: str, from_station: str, 
                              to_station: str, train_date: str) -> dict:
        """获取车票价格（需要额外API调用）"""
        try:
            # 这里需要调用12306的价格查询接口
            # 实际实现中需要更多的session管理和认证
            url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
            
            from_code = await self.station_service.get_station_code(from_station)
            to_code = await self.station_service.get_station_code(to_station)
            
            params = {
                'train_no': train_no,
                'from_station_no': from_code,
                'to_station_no': to_code,
                'seat_types': 'OM9',
                'train_date': train_date
            }
            
            async with self.http_client:
                response = await self.http_client.get(url, params=params)
                return response.json()
                
        except Exception as e:
            logger.error(f"获取票价失败: {e}")
            return {}