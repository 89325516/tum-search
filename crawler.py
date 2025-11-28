"""
优化的爬虫模块 - 支持同步和异步两种模式
兼容原有 SmartCrawler 接口，同时提供高性能的异步批量处理能力
"""
import asyncio
import aiohttp
import math
import logging
import re
import requests
import time
import traceback
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment
from collections import Counter
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor

try:
    from fake_useragent import UserAgent
    HAS_FAKE_USERAGENT = True
except ImportError:
    HAS_FAKE_USERAGENT = False
    logging.warning("fake_useragent not installed, using default User-Agent")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SmartCrawler:
    """
    同步爬虫类 - 保持向后兼容
    这是原有接口，确保现有代码可以正常工作
    """
    def __init__(self):
        # 熵值阈值：根据经验，英文/德文自然语言通常在 3.5 到 5.8 之间
        self.MIN_ENTROPY = 3.5
        self.MAX_ENTROPY = 6.0
        self.MIN_LENGTH = 30

    def calculate_shannon_entropy(self, text):
        """计算文本的香农熵 (Shannon Entropy)"""
        if not text:
            return 0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        entropy = -sum([p * math.log(p) / math.log(2.0) for p in prob if p > 0])
        return entropy

    def is_valid_text(self, text):
        """核心过滤器：基于长度和熵值排除无效文本"""
        if len(text) < self.MIN_LENGTH:
            return False, "Too Short"

        entropy = self.calculate_shannon_entropy(text)

        if entropy < self.MIN_ENTROPY:
            return False, f"Low Entropy ({entropy:.2f}) - Likely menu/nav/ad"
        if entropy > self.MAX_ENTROPY:
            return False, f"High Entropy ({entropy:.2f}) - Likely code/hash"

        return True, entropy

    def _normalize_url(self, url):
        """规范化URL：移除fragment，处理末尾斜杠等"""
        if not url:
            return None
        
        # 移除fragment
        url = url.split('#')[0]
        
        # 解析并重建URL以规范化
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        
        # 规范化路径（移除./和../）
        path = parsed.path
        if path:
            parts = path.split('/')
            normalized_parts = []
            for part in parts:
                if part == '..':
                    if normalized_parts:
                        normalized_parts.pop()
                elif part and part != '.':
                    normalized_parts.append(part)
            path = '/' + '/'.join(normalized_parts)
        
        # 重建URL
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def _is_valid_url(self, url):
        """验证URL是否有效"""
        if not url or len(url) > 2048:  # URL长度限制
            return False
        
        parsed = urlparse(url)
        # 只接受http和https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # 过滤无效协议
        if url.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
            return False
        
        return True
    
    def parse(self, url):
        """
        爬取并拆分图文 - 同步接口（向后兼容）
        返回格式: {"url": str, "texts": List[str], "images": List[str], "links": List[str]}
        """
        # 输入验证
        if not url or not isinstance(url, str):
            logger.error(f"Invalid URL input: {url}")
            return None
        
        if not self._is_valid_url(url):
            logger.error(f"Invalid URL format: {url}")
            return None
        
        # 规范化URL
        url = self._normalize_url(url)
        if not url:
            logger.error(f"Failed to normalize URL: {url}")
            return None
        
        try:
            # 改进的HTTP Headers，更像真实浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()

            # 改进的编码检测：优先使用响应声明的编码，否则尝试检测
            if response.encoding:
                try:
                    html = response.text
                except UnicodeDecodeError:
                    # 如果声明的编码失败，尝试UTF-8
                    html = response.content.decode('utf-8', errors='replace')
            else:
                # 尝试多种常见编码
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                html = None
                for encoding in encodings:
                    try:
                        html = response.content.decode(encoding)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                if html is None:
                    # 如果所有编码都失败，使用UTF-8并替换错误字符
                    html = response.content.decode('utf-8', errors='replace')

            # 尝试使用lxml（更快），如果失败则回退到html.parser
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception:
                logger.debug(f"lxml parser failed for {url}, falling back to html.parser")
                soup = BeautifulSoup(html, 'html.parser')

            # 1. 提取图像
            images = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and not src.startswith('data:'):
                    full_url = urljoin(url, src)
                    # 改进的扩展名提取：移除查询参数和fragment
                    ext = full_url.split('.')[-1].lower().split('?')[0].split('#')[0]
                    if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                        images.append(full_url)

            # 1.5 Remove Noise (Navigation, Footer, Scripts, etc.)
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'noscript', 'iframe', 'svg']):
                element.decompose()
            
            # Remove elements with specific classes/ids indicating noise
            noise_keywords = ['menu', 'cookie', 'popup', 'banner', 'sidebar', 'search', 'language', 'login', 'copyright']
            for tag in list(soup.find_all(True)):
                if not hasattr(tag, 'attrs') or tag.attrs is None:
                    continue
                    
                # Check class and id
                classes = tag.get('class', [])
                if isinstance(classes, list):
                    classes = ' '.join(classes)
                ids = tag.get('id', '')
                
                combined = (str(classes) + " " + str(ids)).lower()
                if any(keyword in combined for keyword in noise_keywords):
                    tag.decompose()

            # 移除注释
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # 2. 提取并清洗文本
            text_blocks = []
            # 优先提取正文相关的标签
            for tag in soup.find_all(['p', 'article', 'main', 'section', 'div']):
                text = tag.get_text(strip=True, separator=' ')
                
                # Filter out common UI text
                ui_phrases = [
                    "close menu", "search navigation", "reset search", 
                    "all rights reserved", "privacy policy", "legal notice",
                    "cookie", "accept", "decline", "skip to content"
                ]
                if any(phrase in text.lower() for phrase in ui_phrases):
                    continue
                    
                valid, reason = self.is_valid_text(text)
                if valid:
                    text_blocks.append(text)
            
            # 去重但保留顺序
            text_blocks = list(dict.fromkeys(text_blocks))

            # 3. Extract Links (Recursive Crawling) - 改进：过滤无效链接
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # 过滤无效协议
                if href.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
                    continue
                
                full_url = urljoin(url, href)
                
                # 规范化URL
                parsed = urlparse(full_url)
                if parsed.scheme in ['http', 'https']:
                    # 规范化URL
                    normalized = self._normalize_url(full_url)
                    if normalized and len(normalized) <= 2048:  # URL长度限制
                        links.append(normalized)
            
            # Deduplicate
            links = list(dict.fromkeys(links))

            return {
                "url": url,
                "texts": text_blocks,
                "images": images[:5],  # 限制每页最多取前5张图
                "links": links
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Crawler Error for {url}: {e}")
            traceback.print_exc()
            return None


class OptimizedCrawler:
    """
    优化的异步爬虫类 - 支持批量并发处理和深度递归爬取
    提供高性能的异步爬取能力，同时保持与 SmartCrawler 兼容的返回格式
    """
    def __init__(self, concurrency=5, timeout=10, delay=1.0, max_rate=None, max_redirects=5, verify_ssl=True, 
                 enable_cache=True, max_cache_size=1000, same_domain_only=True, max_path_depth=None,
                 exclude_static=True, exclude_extensions=None):
        """
        Args:
            concurrency: 并发数，防止封IP
            timeout: 请求超时时间（秒）
            delay: 请求之间的最小延迟（秒），防止请求过于频繁
            max_rate: 全局最大请求速率（每秒请求数），None表示不限制
            max_redirects: 最大重定向深度，防止无限循环
            verify_ssl: 是否验证SSL证书（默认True，生产环境建议启用）
            enable_cache: 是否启用URL缓存，避免重复爬取
            max_cache_size: 最大缓存大小（URL数量）
            same_domain_only: 是否只爬取同一域名（深度爬取时）
            max_path_depth: 最大路径深度限制（None表示不限制）
            exclude_static: 是否排除静态资源文件
            exclude_extensions: 要排除的文件扩展名列表（默认: pdf, jpg, png, gif, css, js等）
        """
        if HAS_FAKE_USERAGENT:
            self.ua = UserAgent()
        else:
            self.ua = None
        
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.executor = ThreadPoolExecutor(max_workers=4)  # 用于CPU密集型任务
        
        # 反爬虫：请求延迟和速率限制
        self.delay = delay  # 请求之间的最小延迟
        self.last_request_time = {}  # 按域名记录最后请求时间
        self.max_rate = max_rate  # 全局速率限制
        self.max_redirects = max_redirects  # 最大重定向深度
        self.verify_ssl = verify_ssl  # SSL验证
        
        # 线程安全：使用锁保护共享状态
        self._rate_limit_lock = asyncio.Lock()
        self._domain_delay_lock = asyncio.Lock()
        self._last_url_lock = asyncio.Lock()
        
        self.rate_limiter = None
        if max_rate:
            # 使用令牌桶算法实现速率限制
            self.rate_limiter = {
                'tokens': max_rate,
                'last_update': time.time(),
                'max_tokens': max_rate
            }
        
        # 优化后的阈值
        # 熵值阈值：根据经验，英文/德文自然语言通常在 3.5 到 5.8 之间
        self.MIN_LENGTH = 30
        self.MIN_ENTROPY = 3.5
        self.MAX_ENTROPY = 6.5
        
        # 预编译正则，提升速度
        self.noise_pattern = re.compile(
            r'menu|cookie|popup|banner|sidebar|search|language|login|copyright|footer|header', 
            re.IGNORECASE
        )
        self.clean_tags = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'noscript', 'iframe', 'svg']
        
        # UI短语过滤
        self.ui_phrases = re.compile(
            r'close menu|search navigation|reset search|all rights reserved|privacy policy|legal notice|cookie|accept|decline',
            re.IGNORECASE
        )
        
        # 深度爬取相关配置
        self.enable_cache = enable_cache
        self.max_cache_size = max_cache_size
        self.same_domain_only = same_domain_only
        self.max_path_depth = max_path_depth
        self.exclude_static = exclude_static
        
        # 默认排除的静态资源扩展名
        if exclude_extensions is None:
            exclude_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', 
                                  '.css', '.js', '.zip', '.tar', '.gz', '.xml', '.json',
                                  '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv',
                                  '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        self.exclude_extensions = set(ext.lower() for ext in exclude_extensions)
        
        # URL缓存（用于避免重复爬取）
        self.url_cache = {}  # {url: result}
        self.cache_lock = asyncio.Lock()
        
        # 爬取统计
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_requests': 0
        }

    def _get_user_agent(self):
        """获取User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except:
                pass
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    def _normalize_url(self, url):
        """规范化URL：移除fragment，处理末尾斜杠等"""
        if not url:
            return None
        
        # 移除fragment
        url = url.split('#')[0]
        
        # 解析并重建URL以规范化
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        
        # 规范化路径（移除./和../）
        path = parsed.path
        if path:
            # 简单的路径规范化
            parts = path.split('/')
            normalized_parts = []
            for part in parts:
                if part == '..':
                    if normalized_parts:
                        normalized_parts.pop()
                elif part and part != '.':
                    normalized_parts.append(part)
            path = '/' + '/'.join(normalized_parts)
        
        # 重建URL
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def _is_valid_url(self, url):
        """验证URL是否有效"""
        if not url or len(url) > 2048:  # URL长度限制
            return False
        
        parsed = urlparse(url)
        # 只接受http和https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # 过滤无效协议
        if url.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
            return False
        
        return True
    
    def _is_valid_link_for_crawl(self, url, start_domain=None):
        """
        深度爬取时的链接过滤 - 更严格的验证
        检查静态资源、路径深度、域名等
        """
        if not self._is_valid_url(url):
            return False
        
        parsed = urlparse(url)
        
        # 域名过滤
        if self.same_domain_only and start_domain:
            if parsed.netloc != start_domain:
                return False
        
        # 路径深度限制
        if self.max_path_depth is not None:
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) > self.max_path_depth:
                return False
        
        # 静态资源过滤
        if self.exclude_static:
            # 检查文件扩展名
            path_lower = parsed.path.lower()
            for ext in self.exclude_extensions:
                if path_lower.endswith(ext):
                    return False
            
            # 检查常见的静态资源路径模式
            static_patterns = ['/static/', '/assets/', '/media/', '/files/', 
                             '/downloads/', '/images/', '/img/', '/css/', '/js/']
            if any(pattern in path_lower for pattern in static_patterns):
                return False
        
        return True
    
    async def _get_from_cache(self, url):
        """从缓存获取结果"""
        if not self.enable_cache:
            return None
        
        async with self.cache_lock:
            if url in self.url_cache:
                self.stats['cache_hits'] += 1
                return self.url_cache[url]
        
        self.stats['cache_misses'] += 1
        return None
    
    async def _add_to_cache(self, url, result):
        """添加到缓存"""
        if not self.enable_cache or result is None:
            return
        
        async with self.cache_lock:
            # 如果缓存已满，删除最旧的条目（简单的FIFO策略）
            if len(self.url_cache) >= self.max_cache_size:
                # 删除第一个（最旧的）条目
                if self.url_cache:
                    oldest_url = next(iter(self.url_cache))
                    del self.url_cache[oldest_url]
            
            self.url_cache[url] = result
    
    async def _get_headers(self, url=None):
        """获取完整的HTTP Headers，更像真实浏览器"""
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # 如果有Referer，添加Referer（模拟从其他页面跳转）
        async with self._last_url_lock:
            if url and hasattr(self, '_last_url') and self._last_url:
                parsed_current = urlparse(url)
                parsed_last = urlparse(self._last_url)
                if parsed_current.netloc == parsed_last.netloc:
                    headers['Referer'] = self._last_url
        
        return headers
    
    async def _rate_limit(self):
        """全局速率限制（令牌桶算法）- 线程安全版本"""
        if not self.max_rate:
            return
        
        async with self._rate_limit_lock:
            now = time.time()
            rate_limiter = self.rate_limiter
            
            # 更新令牌
            elapsed = now - rate_limiter['last_update']
            rate_limiter['tokens'] = min(
                rate_limiter['max_tokens'],
                rate_limiter['tokens'] + elapsed * self.max_rate
            )
            rate_limiter['last_update'] = now
            
            # 如果没有令牌，等待
            if rate_limiter['tokens'] < 1:
                wait_time = (1 - rate_limiter['tokens']) / self.max_rate
                # 释放锁后等待，避免阻塞其他请求
                await asyncio.sleep(wait_time)
                # 重新获取锁并更新
                async with self._rate_limit_lock:
                    rate_limiter['tokens'] = 0
            
            # 消耗一个令牌
            rate_limiter['tokens'] -= 1
    
    async def _domain_delay(self, url):
        """按域名延迟，防止对同一域名请求过于频繁 - 线程安全版本"""
        if self.delay <= 0:
            return
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        async with self._domain_delay_lock:
            now = time.time()
            
            if domain in self.last_request_time:
                elapsed = now - self.last_request_time[domain]
                if elapsed < self.delay:
                    wait_time = self.delay - elapsed
                    # 释放锁后等待
                    await asyncio.sleep(wait_time)
                    # 重新获取锁并更新
                    async with self._domain_delay_lock:
                        self.last_request_time[domain] = time.time()
                else:
                    self.last_request_time[domain] = now
            else:
                self.last_request_time[domain] = now

    async def fetch(self, session, url, redirect_count=0, redirect_history=None):
        """
        异步获取页面内容，带自动重试和反爬虫措施
        
        Args:
            session: aiohttp会话
            url: 目标URL
            redirect_count: 当前重定向深度
            redirect_history: 重定向历史（用于检测循环）
        """
        # 输入验证
        if not url or not self._is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None
        
        # 规范化URL
        url = self._normalize_url(url)
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
            logger.warning(f"Redirect loop detected: {url} -> {redirect_history}")
            return None
        
        # 反爬虫：速率限制和域名延迟
        await self._rate_limit()
        await self._domain_delay(url)
        
        retries = 3
        for i in range(retries):
            try:
                headers = await self._get_headers(url)
                async with self.semaphore:
                    async with session.get(
                        url, 
                        headers=headers, 
                        timeout=self.timeout, 
                        ssl=self.verify_ssl, 
                        allow_redirects=False
                    ) as response:
                        if response.status == 200:
                            # 记录最后访问的URL（用于Referer）
                            async with self._last_url_lock:
                                self._last_url = url
                            # aiohttp会自动检测编码，但添加错误处理
                            try:
                                return await response.text()
                            except UnicodeDecodeError:
                                # 如果自动检测失败，尝试手动解码
                                content = await response.read()
                                # 尝试常见编码
                                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                                for encoding in encodings:
                                    try:
                                        return content.decode(encoding)
                                    except (UnicodeDecodeError, LookupError):
                                        continue
                                # 如果所有编码都失败，使用UTF-8并替换错误字符
                                return content.decode('utf-8', errors='replace')
                        elif response.status in [301, 302, 303, 307, 308]:
                            # 处理重定向
                            redirect_url = response.headers.get('Location')
                            if redirect_url:
                                logger.info(f"Redirecting {url} -> {redirect_url} (depth: {redirect_count + 1})")
                                # 处理相对和绝对URL
                                absolute_redirect = urljoin(url, redirect_url)
                                # 规范化重定向URL
                                absolute_redirect = self._normalize_url(absolute_redirect)
                                
                                if absolute_redirect and self._is_valid_url(absolute_redirect):
                                    # 更新重定向历史
                                    new_history = redirect_history | {url}
                                    # 递归处理重定向
                                    return await self.fetch(
                                        session, 
                                        absolute_redirect, 
                                        redirect_count + 1, 
                                        new_history
                                    )
                                else:
                                    logger.warning(f"Invalid redirect URL: {redirect_url}")
                        else:
                            logger.warning(f"Status {response.status} for {url}")
            except asyncio.TimeoutError:
                logger.debug(f"Timeout {i+1}/{retries} for {url}")
            except aiohttp.ClientError as e:
                logger.debug(f"Client error {i+1}/{retries} for {url}: {e}")
            except Exception as e:
                logger.debug(f"Retry {i+1}/{retries} for {url}: {e}")
            
            if i < retries - 1:
                await asyncio.sleep(2 ** i)  # 指数退避策略
        
        return None

    def fast_entropy(self, text):
        """优化的香农熵计算 (使用了 Counter)"""
        if not text or len(text) < 2:
            return 0
        length = len(text)
        counts = Counter(text)
        probs = (count / length for count in counts.values())
        return -sum(p * math.log2(p) for p in probs if p > 0)

    def clean_dom(self, soup):
        """清洗 DOM 树，移除噪声节点"""
        # 1. 移除无用标签
        for tag in soup(self.clean_tags):
            tag.decompose()
        
        # 2. 移除注释
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 3. 基于 Class/ID 的启发式移除
        for tag in list(soup.find_all(True)):
            attr_str = str(tag.get('class', '')) + " " + str(tag.get('id', ''))
            if self.noise_pattern.search(attr_str):
                tag.decompose()

    def extract_content_smart(self, soup, url):
        """
        智能内容提取：保留段落结构，而不是打散的句子
        返回格式与 SmartCrawler.parse() 兼容
        """
        self.clean_dom(soup)

        # 1. 提取图片
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src or src.startswith('data:'):
                continue
            
            full_url = urljoin(url, src)
            # 改进的扩展名提取：移除查询参数和fragment
            ext = full_url.split('.')[-1].lower().split('?')[0].split('#')[0]
            if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                images.append(full_url)

        # 2. 提取链接（改进：使用增强的链接过滤）
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # 过滤无效协议
            if href.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
                continue
            
            full_link = urljoin(url, href)
            
            # 规范化URL
            normalized = self._normalize_url(full_link)
            if normalized and self._is_valid_url(normalized):
                # 使用增强的链接过滤（如果提供了域名，会进行更严格的检查）
                # 这里只做基本验证，深度爬取时会使用 _is_valid_link_for_crawl
                links.add(normalized)

        # 3. 提取文本 (核心优化：基于块的提取，支持更多内容类型)
        text_blocks = []
        
        # 提取标题（保留层次结构信息）
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = tag.get_text(strip=True, separator=' ')
            if text and len(text) >= 10:  # 标题可以短一些
                text_blocks.append(text)
        
        # 提取段落和主要内容标签
        for tag in soup.find_all(['p', 'article', 'main', 'section', 'div']):
            text = tag.get_text(strip=True, separator=' ')
            
            # 过滤UI短语
            if self.ui_phrases.search(text):
                continue
            
            # 长度检查
            if len(text) < self.MIN_LENGTH:
                continue
            
            # 熵值检查
            entropy = self.fast_entropy(text)
            if self.MIN_ENTROPY <= entropy <= self.MAX_ENTROPY:
                text_blocks.append(text)
        
        # 提取列表项（li标签）- 通常包含有用信息
        for tag in soup.find_all(['li']):
            text = tag.get_text(strip=True, separator=' ')
            # 列表项可以稍短
            if len(text) >= 20 and len(text) < 500:  # 避免过长的列表项
                if self.ui_phrases.search(text):
                    continue
                entropy = self.fast_entropy(text)
                if self.MIN_ENTROPY <= entropy <= self.MAX_ENTROPY:
                    text_blocks.append(text)
        
        # 提取表格内容（td标签）- 某些表格可能包含重要数据
        for tag in soup.find_all(['td', 'th']):
            text = tag.get_text(strip=True, separator=' ')
            if len(text) >= 15 and len(text) < 300:
                if self.ui_phrases.search(text):
                    continue
                entropy = self.fast_entropy(text)
                if self.MIN_ENTROPY <= entropy <= self.MAX_ENTROPY:
                    text_blocks.append(text)
        
        # 提取代码块中的注释和文档字符串（code, pre标签）
        for tag in soup.find_all(['code', 'pre']):
            text = tag.get_text(strip=True)
            # 代码块通常较长，但我们只提取相对短的代码片段或注释
            if len(text) >= 30 and len(text) < 200:
                # 检查是否主要是注释或文档
                if '//' in text or '/*' in text or '#' in text or '"""' in text:
                    text_blocks.append(text)
        
        # 提取块引用（blockquote）- 通常包含重要引用
        for tag in soup.find_all(['blockquote']):
            text = tag.get_text(strip=True, separator=' ')
            if len(text) >= self.MIN_LENGTH:
                entropy = self.fast_entropy(text)
                if self.MIN_ENTROPY <= entropy <= self.MAX_ENTROPY:
                    text_blocks.append(text)

        # 去重但保留顺序
        text_blocks = list(dict.fromkeys(text_blocks))

        # 返回格式与 SmartCrawler 兼容
        return {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "texts": text_blocks,  # 关键：使用 texts 而不是 content_blocks
            "images": images[:5],
            "links": list(links)
        }

    async def process_url(self, session, url):
        """单个 URL 的处理流 - 支持缓存"""
        # 规范化URL
        normalized_url = self._normalize_url(url)
        if not normalized_url:
            return None
        
        # 检查缓存
        cached_result = await self._get_from_cache(normalized_url)
        if cached_result is not None:
            logger.debug(f"Cache hit for {normalized_url}")
            return cached_result
        
        # 统计
        self.stats['total_requests'] += 1
        
        html = await self.fetch(session, normalized_url)
        if not html:
            self.stats['failed_requests'] += 1
            return None

        # 将 CPU 密集型的解析任务放到线程池中，避免阻塞 Event Loop
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(self.executor, self._parse_sync, html, normalized_url)
            # 添加到缓存
            await self._add_to_cache(normalized_url, result)
            return result
        except Exception as e:
            logger.error(f"Parse error {normalized_url}: {e}")
            self.stats['failed_requests'] += 1
            return None

    def _parse_sync(self, html, url):
        """同步解析逻辑 (运行在线程池中) - 带解析器回退"""
        try:
            # 尝试使用lxml（更快），如果失败则回退到html.parser
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception:
                logger.debug(f"lxml parser failed for {url}, falling back to html.parser")
                soup = BeautifulSoup(html, 'html.parser')
            
            return self.extract_content_smart(soup, url)
        except Exception as e:
            logger.error(f"BeautifulSoup parse error for {url}: {e}")
            return None

    async def run(self, urls: List[str]) -> List[Dict]:
        """
        主入口 - 异步批量处理URL列表
        Args:
            urls: URL列表
        Returns:
            成功爬取的结果列表
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤掉异常和None
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {urls[i]}: {result}")
                elif result is not None:
                    valid_results.append(result)
            
            return valid_results

    async def crawl_recursive(self, start_url: str, max_depth: int = 3, max_pages: Optional[int] = None,
                              callback=None, same_domain_only: Optional[bool] = None) -> List[Dict]:
        """
        深度递归爬取 - 使用BFS算法按层爬取
        
        Args:
            start_url: 起始URL
            max_depth: 最大爬取深度（0表示只爬取起始URL）
            max_pages: 最大爬取页面数（None表示不限制）
            callback: 回调函数 callback(count, url, result) 在每个页面爬取完成后调用
            same_domain_only: 是否只爬取同一域名（None表示使用初始化时的设置）
        
        Returns:
            所有爬取结果列表
        """
        if same_domain_only is None:
            same_domain_only = self.same_domain_only
        
        # 规范化起始URL
        start_url = self._normalize_url(start_url)
        if not start_url:
            logger.error(f"Invalid start URL: {start_url}")
            return []
        
        parsed_start = urlparse(start_url)
        start_domain = parsed_start.netloc
        
        visited = set()  # 已访问的URL集合
        queue = [(start_url, 0)]  # (url, depth) 队列，BFS
        results = []
        count = 0
        
        logger.info(f"🚀 Starting recursive crawl from {start_url} (max_depth={max_depth}, max_pages={max_pages or 'unlimited'})")
        
        async with aiohttp.ClientSession() as session:
            while queue:
                # 检查是否达到最大页面数限制
                if max_pages and count >= max_pages:
                    logger.info(f"Reached max_pages limit: {max_pages}")
                    break
                
                # 获取当前层的所有URL（同一深度的URL）
                current_level = []
                current_depth = queue[0][1] if queue else -1
                
                # 收集同一深度的所有URL
                while queue and queue[0][1] == current_depth:
                    url, depth = queue.pop(0)
                    if url not in visited:
                        visited.add(url)
                        current_level.append((url, depth))
                
                if not current_level:
                    break
                
                # 并发爬取当前层的所有URL
                tasks = [self.process_url(session, url) for url, _ in current_level]
                level_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理当前层的结果
                for i, (url, depth) in enumerate(current_level):
                    result = level_results[i]
                    
                    if isinstance(result, Exception):
                        logger.error(f"Error processing {url}: {result}")
                        continue
                    
                    if result is None:
                        continue
                    
                    results.append(result)
                    count += 1
                    
                    # 调用回调函数
                    if callback:
                        try:
                            callback(count, url, result)
                        except Exception as e:
                            logger.warning(f"Callback error for {url}: {e}")
                    
                    logger.info(f"[{count}] Depth {depth}: {url} - Found {len(result.get('texts', []))} text blocks, {len(result.get('links', []))} links")
                    
                    # 如果还有深度，收集下一层的链接
                    if depth < max_depth:
                        links = result.get('links', [])
                        for link in links:
                            # 规范化链接
                            normalized_link = self._normalize_url(link)
                            if not normalized_link:
                                continue
                            
                            # 使用增强的链接过滤
                            if self._is_valid_link_for_crawl(normalized_link, start_domain if same_domain_only else None):
                                if normalized_link not in visited:
                                    # 避免重复添加到队列
                                    if not any(nl == normalized_link for nl, _ in queue):
                                        queue.append((normalized_link, depth + 1))
                
                logger.info(f"Completed depth {current_depth}: processed {len(current_level)} pages, found {len(queue)} URLs for next level")
        
        logger.info(f"✅ Recursive crawl finished. Processed {count} pages in total.")
        return results

    def parse(self, url: str) -> Optional[Dict]:
        """
        同步接口 - 兼容 SmartCrawler.parse()
        为了向后兼容，提供同步接口
        """
        # 输入验证
        if not url or not isinstance(url, str):
            logger.error(f"Invalid URL input: {url}")
            return None
        
        if not self._is_valid_url(url):
            logger.error(f"Invalid URL format: {url}")
            return None
        
        try:
            # 使用同步方式调用异步方法
            try:
                loop = asyncio.get_running_loop()
                # 如果事件循环已经在运行，使用线程池
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.run([url]))
                    results = future.result(timeout=60)  # 添加超时
                    return results[0] if results else None
            except RuntimeError:
                # 没有运行中的事件循环，直接使用asyncio.run
                results = asyncio.run(self.run([url]))
                return results[0] if results else None
        except Exception as e:
            logger.error(f"Error in parse({url}): {e}")
            return None

    def get_stats(self):
        """获取爬取统计信息"""
        cache_hit_rate = 0
        if self.stats['total_requests'] + self.stats['cache_hits'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (self.stats['total_requests'] + self.stats['cache_hits'])
        
        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cache_size': len(self.url_cache),
            'max_cache_size': self.max_cache_size
        }
    
    def clear_cache(self):
        """清空URL缓存"""
        async with self.cache_lock:
            self.url_cache.clear()
            logger.info("Cache cleared")
    
    def close(self):
        """显式关闭资源（推荐使用）"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    
    def __del__(self):
        """清理资源（备用方法）"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except:
            pass  # 忽略清理时的错误
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False


# 为了向后兼容，默认导出 SmartCrawler
# 如果项目需要高性能，可以改用 OptimizedCrawler
if __name__ == "__main__":
    import time
    
    # 测试 SmartCrawler (同步)
    print("=" * 60)
    print("Testing SmartCrawler (Synchronous)")
    print("=" * 60)
    crawler_sync = SmartCrawler()
    start = time.time()
    result = crawler_sync.parse("https://www.tum.de/en/")
    end = time.time()
    
    if result:
        print(f"\n✅ Crawled in {end - start:.2f} seconds")
        print(f"📄 Title: {result.get('title', 'N/A')}")
        print(f"📝 Text blocks: {len(result['texts'])}")
        print(f"🖼️ Images: {len(result['images'])}")
        print(f"🔗 Links: {len(result['links'])}")
        print("\n📝 Sample texts:")
        for i, text in enumerate(result['texts'][:3], 1):
            print(f"   {i}. {text[:80]}...")
    
    # 测试 OptimizedCrawler (异步)
    print("\n" + "=" * 60)
    print("Testing OptimizedCrawler (Asynchronous)")
    print("=" * 60)
    crawler_async = OptimizedCrawler(concurrency=3)
    
    target_urls = [
        "https://www.tum.de/en/",
        "https://www.tum.de/en/studies/",
        "https://www.tum.de/en/research/"
    ]
    
    start = time.time()
    results = asyncio.run(crawler_async.run(target_urls))
    end = time.time()
    
    print(f"\n✅ Crawled {len(results)} pages in {end - start:.2f} seconds")
    for result in results:
        if result:
            print(f"\n📄 {result['url']}")
            print(f"   Texts: {len(result['texts'])} | Images: {len(result['images'])} | Links: {len(result['links'])}")
