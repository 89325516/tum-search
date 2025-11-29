"""
内容过滤模块：文本过滤、链接过滤、噪声移除等
"""
import re
from typing import List, Set, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
from .utils import is_valid_text, filter_static_extensions, get_domain, absolute_url, normalize_url


class ContentFilter:
    """内容过滤器"""
    
    def __init__(self, min_length: int = 30, min_entropy: float = 3.5, max_entropy: float = 6.5):
        """
        初始化内容过滤器
        
        Args:
            min_length: 最小文本长度
            min_entropy: 最小熵值
            max_entropy: 最大熵值
        """
        self.MIN_LENGTH = min_length
        self.MIN_ENTROPY = min_entropy
        self.MAX_ENTROPY = max_entropy
        
        # 预编译正则
        self.noise_pattern = re.compile(
            r'menu|cookie|popup|banner|sidebar|search|language|login|copyright|footer|header',
            re.IGNORECASE
        )
        
        self.ui_phrases = re.compile(
            r'close menu|search navigation|reset search|all rights reserved|privacy policy|legal notice|cookie|accept|decline',
            re.IGNORECASE
        )
        
        # 需要移除的标签
        self.clean_tags = [
            'script', 'style', 'nav', 'footer', 'header', 'aside',
            'form', 'noscript', 'iframe', 'svg', 'button', 'input'
        ]
    
    def clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        清理HTML，移除噪声元素
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            清理后的BeautifulSoup对象
        """
        # 移除注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # 移除不需要的标签
        for tag_name in self.clean_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # 移除类名或ID包含噪声关键词的元素
        for element in soup.find_all(class_=self.noise_pattern):
            element.decompose()
        
        for element in soup.find_all(id=self.noise_pattern):
            element.decompose()
        
        return soup
    
    def extract_text_blocks(self, soup: BeautifulSoup) -> List[str]:
        """
        提取文本块（带过滤）
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            有效的文本块列表
        """
        text_blocks = []
        
        # 优先提取的标签（按重要性排序）
        priority_tags = ['p', 'article', 'main', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        # 先提取优先级标签
        for tag_name in priority_tags:
            for tag in soup.find_all(tag_name):
                text = self._extract_text_from_tag(tag)
                if text:
                    text_blocks.append(text)
        
        # 提取列表项
        for li in soup.find_all(['li', 'dd', 'dt']):
            text = self._extract_text_from_tag(li)
            if text:
                text_blocks.append(text)
        
        # 提取表格单元格
        for td in soup.find_all('td'):
            text = self._extract_text_from_tag(td)
            if text:
                text_blocks.append(text)
        
        # 过滤文本块
        valid_blocks = []
        for text in text_blocks:
            is_valid, _ = is_valid_text(
                text,
                min_length=self.MIN_LENGTH,
                min_entropy=self.MIN_ENTROPY,
                max_entropy=self.MAX_ENTROPY
            )
            
            # 额外检查UI短语
            if is_valid and not self.ui_phrases.search(text):
                valid_blocks.append(text)
        
        # 去重但保留顺序
        return list(dict.fromkeys(valid_blocks))
    
    def _extract_text_from_tag(self, tag) -> str:
        """从标签中提取纯文本"""
        text = tag.get_text(separator=' ', strip=True)
        return text.strip()
    
    def extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL（用于相对路径）
            
        Returns:
            图片URL列表
        """
        images = []
        seen = set()
        
        # 支持的图片扩展名
        image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}
        
        # 查找所有img标签
        for img in soup.find_all('img'):
            # 尝试多个属性
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                src = img.get(attr)
                if src:
                    # 处理相对路径
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        from urllib.parse import urljoin
                        src = urljoin(base_url, src)
                    
                    # 规范化URL
                    from .utils import normalize_url
                    normalized = normalize_url(src)
                    if normalized and normalized not in seen:
                        # 检查扩展名
                        ext = normalized.split('.')[-1].lower().split('?')[0]
                        if ext in image_extensions:
                            images.append(normalized)
                            seen.add(normalized)
                            break
        
        return images[:5]  # 限制每页最多5张图


class LinkFilter:
    """链接过滤器"""
    
    def __init__(
        self,
        same_domain_only: bool = True,
        exclude_static: bool = True,
        exclude_extensions: Optional[Set[str]] = None,
        max_path_depth: Optional[int] = None
    ):
        """
        初始化链接过滤器
        
        Args:
            same_domain_only: 是否只爬取同一域名
            exclude_static: 是否排除静态资源
            exclude_extensions: 要排除的扩展名集合
            max_path_depth: 最大路径深度（None表示智能判断）
        """
        self.same_domain_only = same_domain_only
        self.exclude_static = exclude_static
        self.exclude_extensions = exclude_extensions
        self.max_path_depth = max_path_depth
        
        # 高质量URL模式（用于路径深度判断）
        self.high_quality_patterns = [
            (re.compile(r'/article/|/post/|/page/|/blog/'), True),
            (re.compile(r'/course/|/program/|/study/'), True),
            (re.compile(r'/research/|/publication/|/paper/'), True),
        ]
    
    def is_valid_link(
        self,
        url: str,
        start_domain: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> bool:
        """
        检查链接是否有效
        
        Args:
            url: 链接URL
            start_domain: 起始域名（用于域名过滤）
            base_url: 基础URL（用于路径深度判断）
            
        Returns:
            是否有效
        """
        from .utils import is_valid_url
        
        # 基本URL验证
        if not is_valid_url(url):
            return False
        
        parsed = urlparse(url)
        
        # 域名过滤
        if self.same_domain_only and start_domain:
            if parsed.netloc != start_domain:
                return False
        
        # 静态资源过滤
        if self.exclude_static:
            if filter_static_extensions(url, self.exclude_extensions):
                return False
        
        # 路径深度检查
        if self.max_path_depth is not None:
            path_parts = [p for p in parsed.path.split('/') if p]
            depth = len(path_parts)
            
            # 对于高质量URL，允许更深路径
            is_high_quality = any(
                pattern.search(url) for pattern, _ in self.high_quality_patterns
            )
            
            max_allowed = (self.max_path_depth + 2) if is_high_quality else self.max_path_depth
            
            if depth > max_allowed:
                return False
        
        return True
    
    def extract_links(self, soup: BeautifulSoup, base_url: str, start_domain: Optional[str] = None) -> List[str]:
        """
        提取链接并过滤
        
        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL
            start_domain: 起始域名
            
        Returns:
            有效的链接URL列表
        """
        links = []
        seen = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # 转换为绝对URL
            absolute = absolute_url(base_url, href)
            if not absolute:
                continue
            
            # 规范化URL
            normalized = normalize_url(absolute)
            if not normalized or normalized in seen:
                continue
            
            # 过滤检查
            if self.is_valid_link(normalized, start_domain, base_url):
                links.append(normalized)
                seen.add(normalized)
        
        return links
