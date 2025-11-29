"""
新版模块化爬虫 - 统一异步接口，支持robots.txt、内容去重等高级功能
"""
from .crawler import AsyncCrawler
from .sync_wrapper import SyncCrawlerWrapper

# 导出主要类
__all__ = ['AsyncCrawler', 'SyncCrawlerWrapper']

# 为了向后兼容，提供一个默认的同步接口
def get_crawler(sync=True):
    """
    获取爬虫实例（向后兼容）
    
    Args:
        sync: 如果True，返回同步包装器；如果False，返回异步爬虫
    
    Returns:
        SyncCrawlerWrapper 或 AsyncCrawler 实例
    """
    if sync:
        return SyncCrawlerWrapper()
    else:
        return AsyncCrawler()
