"""
核心异步爬虫类 - 统一异步接口，模块化设计
"""
import asyncio
import aiohttp
import logging
import time
from typing import List, Dict, Optional, Set, Callable
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from .utils import normalize_url, is_valid_url, content_hash, get_domain
from .filters import ContentFilter, LinkFilter
from .robots import RobotsChecker

try:
    from fake_useragent import UserAgent
    HAS_FAKE_USERAGENT = True
except ImportError:
    HAS_FAKE_USERAGENT = False

logger = logging.getLogger(__name__)


class AsyncCrawler:
    """
    统一的异步爬虫类 - 模块化设计，支持robots.txt、内容去重等高级功能
    """
    
    def __init__(
        self,
        concurrency: int = 5,
        timeout: int = 10,
        delay: float = 1.0,
        max_rate: Optional[float] = None,
        max_redirects: int = 5,
        verify_ssl: bool = True,
        enable_cache: bool = True,
        max_cache_size: int = 3000,
        same_domain_only: bool = True,
        max_path_depth: Optional[int] = None,
        exclude_static: bool = True,
        exclude_extensions: Optional[Set[str]] = None,
        enable_robots: bool = True,
        enable_content_dedup: bool = True,
        user_agent: Optional[str] = None
    ):
        """
        初始化异步爬虫
        
        Args:
            concurrency: 并发数
            timeout: 请求超时时间（秒）
            delay: 请求之间的最小延迟（秒）
            max_rate: 全局最大请求速率（每秒请求数）
            max_redirects: 最大重定向深度
            verify_ssl: 是否验证SSL证书
            enable_cache: 是否启用URL缓存
            max_cache_size: 最大缓存大小
            same_domain_only: 是否只爬取同一域名
            max_path_depth: 最大路径深度限制
            exclude_static: 是否排除静态资源
            exclude_extensions: 要排除的文件扩展名列表
            enable_robots: 是否启用robots.txt检查
            enable_content_dedup: 是否启用内容去重
            user_agent: 自定义User-Agent（None表示自动生成）
        """
        # 基础配置
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay = delay
        self.max_rate = max_rate
        self.max_redirects = max_redirects
        self.verify_ssl = verify_ssl
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(concurrency)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 缓存和去重
        self.enable_cache = enable_cache
        self.max_cache_size = max_cache_size
        self.url_cache: Dict[str, Dict] = {}
        self.content_hashes: Set[str] = set()
        self.enable_content_dedup = enable_content_dedup
        
        # 线程安全锁
        self._rate_limit_lock = asyncio.Lock()
        self._domain_delay_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._last_request_time: Dict[str, float] = {}
        
        # 速率限制器
        self.rate_limiter = None
        if max_rate:
            self.rate_limiter = {
                'tokens': max_rate,
                'last_update': time.time(),
                'max_tokens': max_rate
            }
        
        # User-Agent
        if HAS_FAKE_USERAGENT:
            try:
                self.ua = UserAgent()
            except:
                self.ua = None
        else:
            self.ua = None
        self.default_user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        # 过滤器和检查器
        self.content_filter = ContentFilter()
        self.link_filter = LinkFilter(
            same_domain_only=same_domain_only,
            exclude_static=exclude_static,
            exclude_extensions=exclude_extensions,
            max_path_depth=max_path_depth
        )
        
        # robots.txt检查器
        self.robots_checker = None
        if enable_robots:
            self.robots_checker = RobotsChecker(user_agent=self.default_user_agent)
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'content_dedup_count': 0,
            'robots_blocked': 0
        }
        
        self._last_url: Optional[str] = None
    
    def _get_user_agent(self) -> str:
        """获取User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except:
                pass
        return self.default_user_agent
    
    async def _rate_limit(self):
        """全局速率限制（令牌桶算法）"""
        if not self.max_rate:
            return
        
        async with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self.rate_limiter['last_update']
            
            # 补充令牌
            self.rate_limiter['tokens'] = min(
                self.rate_limiter['max_tokens'],
                self.rate_limiter['tokens'] + elapsed * self.max_rate
            )
            self.rate_limiter['last_update'] = now
            
            # 检查是否有足够的令牌
            if self.rate_limiter['tokens'] < 1.0:
                sleep_time = (1.0 - self.rate_limiter['tokens']) / self.max_rate
                await asyncio.sleep(sleep_time)
                self.rate_limiter['tokens'] = 1.0
            
            # 消耗令牌
            self.rate_limiter['tokens'] -= 1.0
    
    async def _domain_delay(self, url: str):
        """按域名延迟，防止对同一域名请求过于频繁"""
        if self.delay <= 0:
            return
        
        domain = get_domain(url)
        if not domain:
            return
        
        async with self._domain_delay_lock:
            last_time = self._last_request_time.get(domain, 0)
            elapsed = time.time() - last_time
            
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            
            self._last_request_time[domain] = time.time()
    
    def _get_headers(self, url: Optional[str] = None) -> Dict[str, str]:
        """获取HTTP Headers"""
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 添加Referer（模拟页面跳转）
        if url and self._last_url:
            headers['Referer'] = self._last_url
        
        return headers
    
    async def fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        redirect_count: int = 0,
        redirect_history: Optional[Set[str]] = None
    ) -> Optional[str]:
        """
        异步获取页面内容，带自动重试和反爬虫措施
        """
        # 输入验证
        if not url or not is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None
        
        # 规范化URL
        url = normalize_url(url)
        if not url:
            logger.warning(f"Failed to normalize URL: {url}")
            return None
        
        # 检查重定向深度
        if redirect_count >= self.max_redirects:
            logger.warning(f"Max redirects ({self.max_redirects}) reached for {url}")
            return None
        
        # 初始化重定向历史
        if redirect_history is None:
            redirect_history = set()
        
        # 检查重定向循环
        if url in redirect_history:
            logger.warning(f"Redirect loop detected: {url}")
            return None
        
        # 反爬虫：速率限制和域名延迟
        await self._rate_limit()
        await self._domain_delay(url)
        
        # 重试逻辑
        retries = 3
        for i in range(retries):
            try:
                headers = self._get_headers(url)
                async with self.semaphore:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=self.timeout,
                        ssl=self.verify_ssl,
                        allow_redirects=False
                    ) as response:
                        if response.status == 200:
                            self._last_url = url
                            try:
                                return await response.text()
                            except UnicodeDecodeError:
                                # 手动解码
                                content = await response.read()
                                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                                    try:
                                        return content.decode(encoding)
                                    except (UnicodeDecodeError, LookupError):
                                        continue
                                return content.decode('utf-8', errors='replace')
                        
                        elif response.status in [301, 302, 303, 307, 308]:
                            # 处理重定向
                            redirect_url = response.headers.get('Location')
                            if redirect_url:
                                absolute_redirect = urljoin(url, redirect_url)
                                absolute_redirect = normalize_url(absolute_redirect)
                                
                                if absolute_redirect and is_valid_url(absolute_redirect):
                                    new_history = redirect_history | {url}
                                    return await self.fetch(
                                        session,
                                        absolute_redirect,
                                        redirect_count + 1,
                                        new_history
                                    )
                        
                        else:
                            logger.warning(f"Status {response.status} for {url}")
            
            except asyncio.TimeoutError:
                logger.debug(f"Timeout {i+1}/{retries} for {url}")
            except aiohttp.ClientError as e:
                logger.debug(f"Client error {i+1}/{retries} for {url}: {e}")
            except Exception as e:
                logger.debug(f"Retry {i+1}/{retries} for {url}: {e}")
            
            # 指数退避
            if i < retries - 1:
                await asyncio.sleep(2 ** i)
        
        return None
    
    async def _get_from_cache(self, url: str) -> Optional[Dict]:
        """从缓存获取结果"""
        if not self.enable_cache:
            return None
        
        async with self._cache_lock:
            return self.url_cache.get(url)
    
    async def _add_to_cache(self, url: str, result: Dict):
        """添加到缓存"""
        if not self.enable_cache or result is None:
            return
        
        async with self._cache_lock:
            # 如果缓存已满，删除最旧的条目
            if len(self.url_cache) >= self.max_cache_size:
                # 删除第一个条目
                oldest_url = next(iter(self.url_cache))
                del self.url_cache[oldest_url]
            
            self.url_cache[url] = result
    
    def _parse_sync(self, html: str, url: str) -> Optional[Dict]:
        """同步解析逻辑（在线程池中运行）"""
        try:
            # 尝试使用lxml，回退到html.parser
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception:
                soup = BeautifulSoup(html, 'html.parser')
            
            # 清理HTML
            soup = self.content_filter.clean_html(soup)
            
            # 提取内容
            texts = self.content_filter.extract_text_blocks(soup)
            
            # 内容去重
            if self.enable_content_dedup:
                deduped_texts = []
                for text in texts:
                    text_hash = content_hash(text)
                    if text_hash not in self.content_hashes:
                        self.content_hashes.add(text_hash)
                        deduped_texts.append(text)
                    else:
                        self.stats['content_dedup_count'] += 1
                texts = deduped_texts
            
            # 提取图片
            images = self.content_filter.extract_images(soup, url)
            
            # 提取链接
            start_domain = get_domain(url)
            links = self.link_filter.extract_links(soup, url, start_domain)
            
            return {
                'url': url,
                'texts': texts,
                'images': images,
                'links': links
            }
        
        except Exception as e:
            logger.error(f"Parse error for {url}: {e}")
            return None
    
    async def process_url(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """处理单个URL"""
        # 规范化URL
        normalized_url = normalize_url(url)
        if not normalized_url:
            return None
        
        # robots.txt检查
        if self.robots_checker:
            can_fetch = await self.robots_checker.can_fetch(normalized_url)
            if not can_fetch:
                logger.info(f"Blocked by robots.txt: {normalized_url}")
                self.stats['robots_blocked'] += 1
                return None
        
        # 检查缓存
        cached_result = await self._get_from_cache(normalized_url)
        if cached_result is not None:
            self.stats['cache_hits'] += 1
            return cached_result
        
        # 统计
        self.stats['total_requests'] += 1
        
        # 获取HTML
        html = await self.fetch(session, normalized_url)
        if not html:
            self.stats['failed_requests'] += 1
            return None
        
        # 解析（在线程池中）
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                self.executor,
                self._parse_sync,
                html,
                normalized_url
            )
            
            if result:
                await self._add_to_cache(normalized_url, result)
            
            return result
        
        except Exception as e:
            logger.error(f"Process error for {normalized_url}: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    async def run(self, urls: List[str]) -> List[Dict]:
        """
        批量处理URL列表
        
        Args:
            urls: URL列表
            
        Returns:
            成功爬取的结果列表
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤异常和None
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {urls[i]}: {result}")
                elif result is not None:
                    valid_results.append(result)
            
            return valid_results
    
    async def crawl_recursive(
        self,
        start_url: str,
        max_depth: int = 8,
        max_pages: Optional[int] = None,
        callback: Optional[Callable[[int, str, Dict], None]] = None,
        same_domain_only: Optional[bool] = None,
        adaptive_depth: bool = True
    ) -> List[Dict]:
        """
        递归爬取（BFS）
        
        Args:
            start_url: 起始URL
            max_depth: 最大深度
            max_pages: 最大页面数
            callback: 回调函数(count, url, result)
            same_domain_only: 是否只爬取同一域名
            adaptive_depth: 是否自适应深度调整
            
        Returns:
            爬取结果列表
        """
        visited = set()
        queue = [(start_url, 0)]
        results = []
        count = 0
        start_domain = get_domain(start_url)
        
        if same_domain_only is None:
            same_domain_only = self.link_filter.same_domain_only
        
        async with aiohttp.ClientSession() as session:
            while queue:
                if max_pages and count >= max_pages:
                    break
                
                # 获取当前层的所有URL
                current_level = []
                current_depth = queue[0][1] if queue else 0
                
                while queue and queue[0][1] == current_depth:
                    url, depth = queue.pop(0)
                    if url in visited:
                        continue
                    visited.add(url)
                    current_level.append((url, depth))
                
                if not current_level:
                    break
                
                # 并发处理当前层
                tasks = [self.process_url(session, url) for url, _ in current_level]
                level_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for i, (url, depth) in enumerate(current_level):
                    result = level_results[i]
                    
                    if isinstance(result, Exception) or result is None:
                        continue
                    
                    results.append(result)
                    count += 1
                    
                    # 回调
                    if callback:
                        try:
                            callback(count, url, result)
                        except Exception as e:
                            logger.warning(f"Callback error for {url}: {e}")
                    
                    # 添加到下一层
                    if depth < max_depth:
                        for link in result.get('links', []):
                            link_domain = get_domain(link)
                            if link not in visited:
                                if not same_domain_only or link_domain == start_domain:
                                    queue.append((link, depth + 1))
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        cache_hit_rate = 0
        total = self.stats['total_requests'] + self.stats['cache_hits']
        if total > 0:
            cache_hit_rate = self.stats['cache_hits'] / total
        
        async def get_cache_size():
            async with self._cache_lock:
                return len(self.url_cache)
        
        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cache_size': len(self.url_cache),
            'max_cache_size': self.max_cache_size,
            'content_hash_count': len(self.content_hashes)
        }
    
    async def clear_cache(self):
        """清空缓存"""
        async with self._cache_lock:
            self.url_cache.clear()
            self.content_hashes.clear()
    
    async def close(self):
        """关闭爬虫，释放资源"""
        self.executor.shutdown(wait=True)
        if self.robots_checker:
            self.robots_checker.clear_cache()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
