import requests
import math
import traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class SmartCrawler:
    def __init__(self):
        # 熵值阈值：根据经验，英文/德文自然语言通常在 3.5 到 5.8 之间
        self.MIN_ENTROPY = 3.5
        self.MAX_ENTROPY = 6.0
        self.MIN_LENGTH = 50  # 至少50个字符

    def calculate_shannon_entropy(self, text):
        """计算文本的香农熵 (Shannon Entropy)"""
        if not text:
            return 0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        entropy = - sum([p * math.log(p) / math.log(2.0) for p in prob])
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

    def parse(self, url):
        """
        爬取并拆分图文
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (TUM Student Project)'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. 提取图像
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    full_url = urljoin(url, src)
                    # 简单过滤小图标
                    images.append(full_url)

            # 1.5 Remove Noise (Navigation, Footer, Scripts, etc.)
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'noscript']):
                element.decompose()
            
            # Remove elements with specific classes/ids indicating noise
            noise_keywords = ['menu', 'cookie', 'popup', 'banner', 'sidebar', 'search', 'language', 'login']
            # Use a list to avoid modification during iteration issues
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

            # 2. 提取并清洗文本
            text_blocks = []
            # 只看正文相关的标签
            for tag in soup.find_all(['p', 'article', 'div', 'section', 'h1', 'h2', 'h3', 'li']):
                text = tag.get_text(strip=True)
                
                # Filter out common UI text
                ui_phrases = ["close menu", "search navigation", "reset search", "all rights reserved", "privacy policy", "legal notice"]
                if any(phrase in text.lower() for phrase in ui_phrases):
                    continue
                    
                valid, reason = self.is_valid_text(text)
                if valid:
                    text_blocks.append(text)
            
            # 去重
            text_blocks = list(set(text_blocks))

            # 3. Extract Links (Recursive Crawling)
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                # Filter: Only keep http/https and remove fragments
                if full_url.startswith('http'):
                    full_url = full_url.split('#')[0]
                    links.append(full_url)
            
            # Deduplicate
            links = list(set(links))

            return {
                "url": url,
                "texts": text_blocks,
                "images": images[:5],  # 限制每页最多取前5张图
                "links": links
            }

        except Exception as e:
            print(f"Crawler Error for {url}: {e}")
            traceback.print_exc()
            return None


if __name__ == "__main__":
    # 测试一下熵值计算
    crawler = SmartCrawler()
    print("Test Parsing...")
    # 你可以换成任何真实的 URL 测试
    res = crawler.parse("https://www.tum.de/en/")
    if res:
        print(f"Extracted {len(res['texts'])} valid text blocks and {len(res['images'])} images.")
        for t in res['texts'][:3]:
            print(f"Sample Text (Entropy {crawler.calculate_shannon_entropy(t):.2f}): {t[:50]}...")