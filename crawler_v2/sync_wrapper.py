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
        logger.debug(f"SyncCrawlerWrapper.parse() called for: {url}")
        try:
            # 检查是否在已有事件循环的上下文中
            try:
                loop = asyncio.get_running_loop()
                logger.debug(f"Running in existing event loop context, using thread pool")
                # 如果有运行中的循环，在新线程中运行
                import concurrent.futures
                
                def run_in_new_loop():
                    """在新的事件循环中运行（在新线程中）"""
                    logger.debug(f"Creating new event loop in thread")
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        logger.debug(f"Running async crawler for: {url}")
                        results = new_loop.run_until_complete(self.async_crawler.run([url]))
                        logger.debug(f"Async crawler completed, got {len(results) if results else 0} results")
                        return results
                    finally:
                        logger.debug(f"Closing event loop")
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_new_loop)
                    results = future.result(timeout=120)  # 120秒超时
                    return results[0] if results else None
                    
            except RuntimeError:
                # 没有运行中的循环，直接运行
                logger.debug(f"No running event loop, using asyncio.run()")
                results = asyncio.run(self.async_crawler.run([url]))
                return results[0] if results else None
                
        except Exception as e:
            logger.error(f"Error in parse({url}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
