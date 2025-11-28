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
import threading
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
                 enable_cache=True, max_cache_size=3000, same_domain_only=True, max_path_depth=None,
                 exclude_static=True, exclude_extensions=None, enable_link_prioritization=True):
        """
        Args:
            concurrency: 并发数，防止封IP
            timeout: 请求超时时间（秒）
            delay: 请求之间的最小延迟（秒），防止请求过于频繁
            max_rate: 全局最大请求速率（每秒请求数），None表示不限制
            max_redirects: 最大重定向深度，防止无限循环
            verify_ssl: 是否验证SSL证书（默认True，生产环境建议启用）
            enable_cache: 是否启用URL缓存，避免重复爬取
            max_cache_size: 最大缓存大小（URL数量），默认增加到3000以支持更深爬取
            same_domain_only: 是否只爬取同一域名（深度爬取时）
            max_path_depth: 最大路径深度限制（None表示智能判断，基于URL语义，高质量URL允许最多12层）
            exclude_static: 是否排除静态资源文件
            exclude_extensions: 要排除的文件扩展名列表（默认: pdf, jpg, png, gif, css, js等）
            enable_link_prioritization: 是否启用链接优先级评分系统（默认True）
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
        self.enable_link_prioritization = enable_link_prioritization
        
        # 默认排除的静态资源扩展名
        if exclude_extensions is None:
            exclude_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', 
                                  '.css', '.js', '.zip', '.tar', '.gz', '.xml', '.json',
                                  '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv',
                                  '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        self.exclude_extensions = set(ext.lower() for ext in exclude_extensions)
        
        # 链接优先级评分：高质量URL模式（正分）和低质量URL模式（负分）
        self.high_quality_patterns = [
            (re.compile(r'/(article|post|news|blog|page|content|detail|view|show)/', re.I), 3.0),
            (re.compile(r'/(course|program|study|education|research|faculty|department)/', re.I), 2.5),
            (re.compile(r'/(about|info|overview|introduction)/', re.I), 2.0),
            (re.compile(r'/\d{4}/|\d{2}/', re.I), 1.0),  # 日期路径通常表示文章
        ]
        self.low_quality_patterns = [
            (re.compile(r'/(tag|category|author|archive|feed|rss|atom)/', re.I), -2.0),
            (re.compile(r'/(print|pdf|download|export|share|embed)/', re.I), -3.0),
            (re.compile(r'/(search|result|filter|sort)/', re.I), -1.5),
            (re.compile(r'/api/|/ajax/|/json/', re.I), -3.0),
        ]
        
        # 高质量链接文本关键词
        self.high_quality_link_texts = re.compile(
            r'(learn|read|more|details|information|about|study|research|course|program|article|news)',
            re.I
        )
        
        # URL缓存（用于避免重复爬取）
        self.url_cache = {}  # {url: result}
        # 锁机制说明：
        # - cache_lock (asyncio.Lock): 用于异步方法，保护异步代码之间的并发访问
        # - cache_lock_sync (threading.Lock): 用于同步方法，保护跨线程访问
        # 注意：虽然两个锁不能互相保护，但在实际使用中：
        #   - 异步代码主要在单线程事件循环中运行，使用 asyncio.Lock 保护异步并发
        #   - 同步方法可能在另一个线程中，使用 threading.Lock 保护跨线程访问
        self.cache_lock = asyncio.Lock()  # 异步锁，用于异步方法
        self.cache_lock_sync = threading.Lock()  # 同步锁，用于同步方法（修复竞态条件）
        
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
    
    def _score_link_quality(self, url, link_text=None, link_context=None):
        """
        链接质量评分系统 - 根据URL模式、链接文本和上下文评分
        返回评分（0-10），分数越高表示链接质量越好，应该优先爬取
        
        Args:
            url: 链接URL
            link_text: 链接文本内容（可选）
            link_context: 链接上下文信息，如所属标签（可选，如 'nav', 'content', 'footer'）
        
        Returns:
            评分（float），范围通常在 -5 到 10
        """
        score = 5.0  # 基础分
        
        # URL模式评分
        for pattern, points in self.high_quality_patterns:
            if pattern.search(url):
                score += points
        
        for pattern, points in self.low_quality_patterns:
            if pattern.search(url):
                score += points  # points 是负数
        
        # 链接文本评分
        if link_text:
            text_lower = link_text.lower().strip()
            if len(text_lower) > 3:  # 有意义的链接文本
                if self.high_quality_link_texts.search(text_lower):
                    score += 1.0
                # 链接文本太短或太通用，降低分数
                if len(text_lower) < 5:
                    score -= 0.5
                if text_lower in ['more', 'click', 'here', 'link', 'read more']:
                    score -= 1.0
        
        # 上下文位置评分
        if link_context:
            context_lower = link_context.lower()
            if 'content' in context_lower or 'main' in context_lower or 'article' in context_lower:
                score += 1.5
            elif 'nav' in context_lower:
                score += 0.5  # 导航链接有一定价值
            elif 'footer' in context_lower or 'sidebar' in context_lower:
                score -= 0.5
        
        # 路径深度调整：适度深度（2-6层）通常质量更高，但允许更深的路径
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        depth = len(path_parts)
        if 2 <= depth <= 6:
            score += 0.5  # 适度深度加分
        elif 7 <= depth <= 10:
            score += 0.0  # 较深路径不扣分，允许探索
        elif depth > 10:
            score -= 0.5  # 非常深的路径轻微扣分，但仍允许
        
        return max(0.0, min(10.0, score))  # 限制在 0-10 范围
    
    def _is_valid_link_for_crawl(self, url, start_domain=None):
        """
        深度爬取时的链接过滤 - 更严格的验证（增强版：支持智能路径深度判断）
        检查静态资源、路径深度、域名等
        """
        if not self._is_valid_url(url):
            return False
        
        parsed = urlparse(url)
        
        # 域名过滤
        if self.same_domain_only and start_domain:
            if parsed.netloc != start_domain:
                return False
        
        # 智能路径深度限制
        path_parts = [p for p in parsed.path.split('/') if p]
        depth = len(path_parts)
        
        if self.max_path_depth is not None:
            # 硬性限制
            if depth > self.max_path_depth:
                return False
        else:
            # 智能判断：基于URL语义而非简单层级
            # 对于包含高质量关键词的URL，允许更深路径
            is_high_quality = any(
                pattern.search(url) for pattern, _ in self.high_quality_patterns
            )
            # 大幅放宽路径深度限制，支持更深的爬取
            max_allowed_depth = 12 if is_high_quality else 10
            if depth > max_allowed_depth:
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

        # 2. 提取链接（增强版：从更多位置提取，附带元数据用于优先级评分）
        links = []  # 改为列表，存储 (url, metadata) 元组
        links_set = set()  # 用于去重
        
        # 从不同区域提取链接，并标记上下文
        # 修复：语义标签（article, main, section等）应该无条件查找，div标签可以要求匹配class
        def find_content_containers():
            """查找内容容器：语义标签无条件查找，div标签要求匹配class"""
            containers = []
            # 语义标签：无条件查找（这些标签本身就表示内容区域）
            semantic_tags = soup.find_all(['article', 'main', 'section'])
            containers.extend(semantic_tags)
            # div标签：要求匹配class
            div_with_class = soup.find_all('div', class_=re.compile(r'content|main|article|body', re.I))
            containers.extend(div_with_class)
            return containers
        
        def find_nav_containers():
            """查找导航容器：nav和header标签无条件查找，div标签要求匹配class"""
            containers = []
            # 语义标签：无条件查找
            semantic_tags = soup.find_all(['nav', 'header'])
            containers.extend(semantic_tags)
            # div标签：要求匹配class
            div_with_class = soup.find_all('div', class_=re.compile(r'nav|menu|header', re.I))
            containers.extend(div_with_class)
            return containers
        
        def find_sidebar_containers():
            """查找侧边栏容器：aside标签无条件查找，div标签要求匹配class"""
            containers = []
            # 语义标签：无条件查找
            semantic_tags = soup.find_all('aside')
            containers.extend(semantic_tags)
            # div标签：要求匹配class
            div_with_class = soup.find_all('div', class_=re.compile(r'sidebar|aside', re.I))
            containers.extend(div_with_class)
            return containers
        
        def find_footer_containers():
            """查找页脚容器：footer标签无条件查找"""
            # footer是语义标签，无条件查找
            return soup.find_all('footer')
        
        link_sources = [
            ('content', find_content_containers()),
            ('nav', find_nav_containers()),
            ('sidebar', find_sidebar_containers()),
            ('footer', find_footer_containers()),
        ]
        
        # 从各区域提取链接
        for context, containers in link_sources:
            for container in containers:
                for a in container.find_all('a', href=True):
                    href = a['href']
                    
                    # 过滤无效协议
                    if href.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
                        continue
                    
                    full_link = urljoin(url, href)
                    
                    # 规范化URL
                    normalized = self._normalize_url(full_link)
                    if normalized and self._is_valid_url(normalized):
                        if normalized not in links_set:
                            links_set.add(normalized)
                            # 提取链接文本
                            link_text = a.get_text(strip=True)
                            # 存储链接及其元数据
                            links.append((normalized, {'text': link_text, 'context': context}))
        
        # 如果从上述区域没找到足够链接，从整个页面提取（向后兼容）
        if len(links) < 10:
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                if href.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
                    continue
                
                full_link = urljoin(url, href)
                normalized = self._normalize_url(full_link)
                if normalized and self._is_valid_url(normalized):
                    if normalized not in links_set:
                        links_set.add(normalized)
                        link_text = a.get_text(strip=True)
                        # 尝试推断上下文
                        parent_tag = a.find_parent()
                        context = 'general'
                        if parent_tag:
                            parent_class = str(parent_tag.get('class', ''))
                            if any(x in parent_class.lower() for x in ['nav', 'menu']):
                                context = 'nav'
                            elif any(x in parent_class.lower() for x in ['content', 'main', 'article']):
                                context = 'content'
                            elif 'footer' in parent_tag.name.lower() or 'footer' in parent_class.lower():
                                context = 'footer'
                        links.append((normalized, {'text': link_text, 'context': context}))
        
        # 存储链接元数据用于优先级排序（存储在结果中）
        links_metadata = {url: metadata for url, metadata in links}
        links_urls = [url for url, _ in links]
        
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

        # 返回格式与 SmartCrawler 兼容，但增加链接元数据
        result = {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "texts": text_blocks,  # 关键：使用 texts 而不是 content_blocks
            "images": images[:5],
            "links": links_urls,  # URL列表（向后兼容）
            "_links_metadata": links_metadata  # 链接元数据（用于优先级排序）
        }
        return result

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

    def _calculate_page_quality(self, result: Dict) -> float:
        """
        计算页面质量分数（0-10），用于自适应深度调整
        基于文本块数量、文本总长度、链接数量等指标
        """
        if not result:
            return 0.0
        
        score = 0.0
        
        # 文本块数量和长度
        texts = result.get('texts', [])
        if texts:
            text_count = len(texts)
            total_length = sum(len(t) for t in texts)
            
            # 文本块越多越好（但有限制）
            score += min(text_count / 10.0, 3.0)  # 最多3分
            
            # 总长度（内容越丰富越好）
            score += min(total_length / 1000.0, 2.0)  # 最多2分
        
        # 链接数量（适度最好）
        links = result.get('links', [])
        link_count = len(links)
        if 5 <= link_count <= 50:
            score += 2.0  # 链接数量合理
        elif link_count > 50:
            score += 1.0  # 链接太多可能质量较低
        
        # 有标题加分
        title = result.get('title', '').strip()
        if title and len(title) > 10:
            score += 1.0
        
        return min(10.0, score)
    
    async def crawl_recursive(self, start_url: str, max_depth: int = 8, max_pages: Optional[int] = None,
                              callback=None, same_domain_only: Optional[bool] = None, 
                              adaptive_depth: bool = True, max_adaptive_depth: int = 2) -> List[Dict]:
        """
        深度递归爬取 - 使用BFS算法按层爬取，支持链接优先级排序和自适应深度调整
        
        Args:
            start_url: 起始URL
            max_depth: 最大爬取深度（默认8，0表示只爬取起始URL）
            max_pages: 最大爬取页面数（None表示不限制）
            callback: 回调函数 callback(count, url, result) 在每个页面爬取完成后调用
            same_domain_only: 是否只爬取同一域名（None表示使用初始化时的设置）
            adaptive_depth: 是否启用自适应深度调整（默认True，根据页面质量动态调整爬取策略）
            max_adaptive_depth: 自适应深度调整的最大额外深度（默认2，即最多可以到 max_depth + 2）
        
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
                    
                    # 计算页面质量
                    page_quality = self._calculate_page_quality(result) if adaptive_depth else 5.0
                    logger.info(f"[{count}] Depth {depth}: {url} - Found {len(result.get('texts', []))} text blocks, {len(result.get('links', []))} links (quality: {page_quality:.1f})")
                    
                    # 自适应深度调整：如果页面质量高，允许更深爬取
                    effective_max_depth = max_depth
                    if adaptive_depth:
                        if page_quality >= 8.0:
                            # 非常高质量页面，允许最大额外深度
                            effective_max_depth = max_depth + max_adaptive_depth
                            logger.debug(f"Very high quality page detected (quality: {page_quality:.1f}), allowing depth up to {effective_max_depth}")
                        elif page_quality >= 6.0:
                            # 高质量页面，允许中等额外深度
                            effective_max_depth = max_depth + max(1, max_adaptive_depth - 1)
                            logger.debug(f"High quality page detected (quality: {page_quality:.1f}), allowing depth up to {effective_max_depth}")
                        elif page_quality < 2.5:
                            # 低质量页面，提前终止
                            effective_max_depth = depth
                            logger.debug(f"Low quality page detected (quality: {page_quality:.1f}), stopping deep crawl at depth {depth}")
                    
                    # 如果还有深度，收集下一层的链接
                    if depth < effective_max_depth:
                        links = result.get('links', [])
                        links_metadata = result.get('_links_metadata', {})
                        
                        # 收集并评分链接
                        candidate_links = []
                        for link in links:
                            # 规范化链接
                            normalized_link = self._normalize_url(link)
                            if not normalized_link:
                                continue
                            
                            # 使用增强的链接过滤
                            if not self._is_valid_link_for_crawl(normalized_link, start_domain if same_domain_only else None):
                                continue
                            
                            if normalized_link in visited:
                                continue
                            
                            # 避免重复添加到队列
                            if any(nl == normalized_link for nl, _ in queue):
                                continue
                            
                            # 获取链接元数据并评分
                            metadata = links_metadata.get(normalized_link, {})
                            link_text = metadata.get('text', '')
                            link_context = metadata.get('context', 'general')
                            
                            # 链接质量评分
                            if self.enable_link_prioritization:
                                score = self._score_link_quality(normalized_link, link_text, link_context)
                            else:
                                score = 5.0  # 默认分
                            
                            candidate_links.append((normalized_link, depth + 1, score))
                        
                        # 按优先级排序（分数高的优先）
                        if self.enable_link_prioritization:
                            candidate_links.sort(key=lambda x: x[2], reverse=True)
                            logger.debug(f"Sorted {len(candidate_links)} links by priority for depth {depth + 1}")
                        
                        # 添加到队列（按优先级顺序）
                        for normalized_link, new_depth, score in candidate_links:
                            queue.append((normalized_link, new_depth))
                
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
        """获取爬取统计信息（同步方法，使用同步锁保护缓存读取）"""
        cache_hit_rate = 0
        if self.stats['total_requests'] + self.stats['cache_hits'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (self.stats['total_requests'] + self.stats['cache_hits'])
        
        # 使用同步锁保护缓存大小读取，确保数据一致性
        with self.cache_lock_sync:
            cache_size = len(self.url_cache)
        
        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cache_size': cache_size,
            'max_cache_size': self.max_cache_size
        }
    
    async def clear_cache(self):
        """清空URL缓存（异步方法）"""
        async with self.cache_lock:
            self.url_cache.clear()
            logger.info("Cache cleared")
    
    def clear_cache_sync(self):
        """清空URL缓存（同步方法，用于向后兼容）"""
        # 使用同步锁保护，避免与异步方法产生竞态条件
        with self.cache_lock_sync:
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
