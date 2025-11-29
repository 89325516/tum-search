"""
工具函数模块：URL处理、内容哈希、熵值计算等
"""
import re
import hashlib
import math
from urllib.parse import urljoin, urlparse
from typing import Optional, Set


def normalize_url(url: str) -> Optional[str]:
    """
    规范化URL：移除fragment，处理相对路径等
    
    Args:
        url: 原始URL
        
    Returns:
        规范化后的URL，如果无效则返回None
    """
    if not url:
        return None
    
    # 移除fragment
    url = url.split('#')[0].strip()
    
    # 解析并重建URL
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


def is_valid_url(url: str, max_length: int = 2048) -> bool:
    """
    验证URL是否有效
    
    Args:
        url: URL字符串
        max_length: URL最大长度
        
    Returns:
        是否有效
    """
    if not url or len(url) > max_length:
        return False
    
    parsed = urlparse(url)
    # 只接受http和https
    if parsed.scheme not in ['http', 'https']:
        return False
    
    # 过滤无效协议
    if url.lower().startswith(('javascript:', 'mailto:', 'tel:', 'data:', 'file:')):
        return False
    
    return True


def calculate_shannon_entropy(text: str) -> float:
    """
    计算文本的香农熵 (Shannon Entropy)
    
    Args:
        text: 输入文本
        
    Returns:
        熵值
    """
    if not text:
        return 0
    
    prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
    entropy = -sum([p * math.log(p) / math.log(2.0) for p in prob if p > 0])
    return entropy


def is_valid_text(text: str, min_length: int = 30, min_entropy: float = 3.5, max_entropy: float = 6.5) -> tuple[bool, str]:
    """
    检查文本是否有效（基于长度和熵值）
    
    Args:
        text: 文本内容
        min_length: 最小长度
        min_entropy: 最小熵值
        max_entropy: 最大熵值
        
    Returns:
        (是否有效, 原因)
    """
    if len(text) < min_length:
        return False, "Too Short"
    
    entropy = calculate_shannon_entropy(text)
    
    if entropy < min_entropy:
        return False, f"Low Entropy ({entropy:.2f}) - Likely menu/nav/ad"
    if entropy > max_entropy:
        return False, f"High Entropy ({entropy:.2f}) - Likely code/hash"
    
    return True, str(entropy)


def content_hash(text: str) -> str:
    """
    计算内容的MD5哈希值（用于去重）
    
    Args:
        text: 文本内容
        
    Returns:
        MD5哈希值（十六进制字符串）
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def absolute_url(base_url: str, href: str) -> Optional[str]:
    """
    将相对URL转换为绝对URL
    
    Args:
        base_url: 基础URL
        href: 相对或绝对URL
        
    Returns:
        绝对URL，如果无效则返回None
    """
    if not href:
        return None
    
    try:
        absolute = urljoin(base_url, href)
        return normalize_url(absolute)
    except Exception:
        return None


def get_domain(url: str) -> Optional[str]:
    """
    提取URL的域名
    
    Args:
        url: URL字符串
        
    Returns:
        域名，如果无效则返回None
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def filter_static_extensions(url: str, exclude_extensions: Optional[Set[str]] = None) -> bool:
    """
    检查URL是否为静态资源
    
    Args:
        url: URL字符串
        exclude_extensions: 要排除的扩展名集合
        
    Returns:
        如果是静态资源返回True，否则返回False
    """
    if exclude_extensions is None:
        exclude_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
            '.css', '.js', '.ico', '.zip', '.tar', '.gz', '.rar',
            '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }
    
    url_lower = url.lower()
    for ext in exclude_extensions:
        if url_lower.endswith(ext):
            return True
    
    # 检查静态路径模式
    static_patterns = ['/static/', '/assets/', '/media/', '/images/', '/css/', '/js/']
    for pattern in static_patterns:
        if pattern in url_lower:
            return True
    
    return False
