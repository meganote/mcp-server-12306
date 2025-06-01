"""数据模型包"""

from .station import Station, StationSearchResult
from .ticket import Ticket, TicketQuery, TicketSearchResult
from .query import QueryRequest, QueryResponse

__all__ = [
    "Station",
    "StationSearchResult", 
    "Ticket",
    "TicketQuery",
    "TicketSearchResult",
    "QueryRequest",
    "QueryResponse",
]