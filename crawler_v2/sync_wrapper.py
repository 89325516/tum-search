"""
同步包装器 - 为了向后兼容，提供同步接口
"""
import asyncio
import logging
from typing import Optional, Dict
from .crawler import AsyncCrawler

logger = logging.getLogger(__name__)


class SyncCrawlerWrapper:
    """
    同步爬虫包装器 - 包装AsyncCrawler以提供同步接口
    兼容原有的SmartCrawler.parse()接口
    """
    
    def __init__(self, **kwargs):
        """
        初始化同步包装器
        
        Args:
            **kwargs: 传递给AsyncCrawler的参数
        """
        self.async_crawler = AsyncCrawler(**kwargs)
        self._loop = None
    
    def parse(self, url: str) -> Optional[Dict]:
        """
        同步接口 - 兼容SmartCrawler.parse()
        
        Args:
            url: 要爬取的URL
            
        Returns:
            爬取结果字典，格式：{"url": str, "texts": List[str], "images": List[str], "links": List[str]}
            如果失败则返回None
        """
        try:
            # 尝试获取运行中的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果已经有运行中的循环，在线程池中运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._parse_async(url))
                    results = future.result(timeout=60)
                    return results[0] if results else None
            except RuntimeError:
                # 没有运行中的循环，直接运行
                results = asyncio.run(self.async_crawler.run([url]))
                return results[0] if results else None
        except Exception as e:
            logger.error(f"Error in parse({url}): {e}")
            return None
    
    async def _parse_async(self, url: str):
        """内部异步方法"""
        return await self.async_crawler.run([url])
    
    def __getattr__(self, name):
        """代理其他方法到异步爬虫"""
        return getattr(self.async_crawler, name)
    
    def __del__(self):
        """清理资源"""
        try:
            # 尝试关闭异步爬虫
            if hasattr(self.async_crawler, 'executor'):
                self.async_crawler.executor.shutdown(wait=False)
        except Exception:
            pass
