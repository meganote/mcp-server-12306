"""HTTP客户端服务"""

import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from mcp_12306.utils.config import get_settings

logger = logging.getLogger(__name__)


class HttpClient:
    """12306 HTTP客户端"""
    
    def __init__(self):
        self.settings = get_settings()
        self.session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        await self.create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
        
    async def create_session(self):
        """创建HTTP会话"""
        headers = {
            'User-Agent': self.settings.user_agent,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        self.session = httpx.AsyncClient(
            headers=headers,
            timeout=self.settings.request_timeout,
            verify=False,  # 12306证书问题
            follow_redirects=True
        )
        
    async def close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.aclose()
            
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """GET请求"""
        if not self.session:
            await self.create_session()
        assert self.session is not None  # 类型保证
        try:
            logger.info(f"发送GET请求: {url}")
            response = await self.session.get(url, params=params)
            logger.info(f"响应状态: {response.status_code}")
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP状态错误: {e}")
            raise

    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, 
                   json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """POST请求"""
        if not self.session:
            await self.create_session()
        assert self.session is not None  # 类型保证
        try:
            response = await self.session.post(url, data=data, json=json)
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP状态错误: {e}")
            raise