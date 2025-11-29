"""
robots.txt 支持模块
"""
import asyncio
import aiohttp
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)


class RobotsChecker:
    """robots.txt 检查器（异步版本）"""
    
    def __init__(self, user_agent: str = '*', timeout: int = 5):
        """
        初始化robots.txt检查器
        
        Args:
            user_agent: User-Agent字符串（默认'*'表示所有）
            timeout: 请求超时时间（秒）
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: Dict[str, tuple[RobotFileParser, float]] = {}
        self._cache_ttl = 3600  # 缓存1小时
    
    async def can_fetch(self, url: str) -> bool:
        """
        检查是否可以爬取指定URL
        
        Args:
            url: 要检查的URL
            
        Returns:
            是否可以爬取
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # 检查缓存
        if robots_url in self._cache:
            rp, cached_time = self._cache[robots_url]
            if time.time() - cached_time < self._cache_ttl:
                return rp.can_fetch(self.user_agent, url)
        
        # 获取robots.txt
        rp = await self._fetch_robots(robots_url)
        if rp is None:
            # 如果无法获取robots.txt，默认允许爬取
            return True
        
        # 缓存结果
        self._cache[robots_url] = (rp, time.time())
        
        return rp.can_fetch(self.user_agent, url)
    
    async def _fetch_robots(self, robots_url: str) -> Optional[RobotFileParser]:
        """
        获取并解析robots.txt
        
        Args:
            robots_url: robots.txt的URL
            
        Returns:
            RobotFileParser对象，如果失败则返回None
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        # 手动解析robots.txt内容
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        # 手动解析内容
                        lines = content.splitlines()
                        for line in lines:
                            # 忽略空行和注释
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            rp.feed(line)
                        return rp
                    else:
                        # 如果没有robots.txt（404），默认允许
                        return None
        except Exception as e:
            # 如果出错，默认允许爬取（不阻塞）
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return None
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
