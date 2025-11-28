import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import argparse
from system_manager import SystemManager

class AutoCrawler:
    def __init__(self, start_url, max_depth=2, max_pages=50):
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited = set()
        self.to_visit = [(start_url, 0)] # (url, depth)
        self.mgr = SystemManager()
        self.domain = urlparse(start_url).netloc
        self.processed_count = 0

    def is_valid_url(self, url):
        parsed = urlparse(url)
        # Only crawl same domain
        if parsed.netloc != self.domain:
            return False
        # Filter static assets
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.css', '.js', '.zip']):
            return False
        return True

    def get_links(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (TUM Student Project)'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                # Remove fragment
                full_url = full_url.split('#')[0]
                if self.is_valid_url(full_url) and full_url not in self.visited:
                    links.append(full_url)
            return links
        except Exception as e:
            print(f"⚠️ Error fetching links from {url}: {e}")
            return []

    def run(self):
        print(f"🚀 Starting Auto-Crawler on {self.start_url}")
        print(f"   Max Depth: {self.max_depth}, Max Pages: {self.max_pages}")
        
        while self.to_visit and self.processed_count < self.max_pages:
            current_url, depth = self.to_visit.pop(0)
            
            if current_url in self.visited:
                continue
            
            self.visited.add(current_url)
            self.processed_count += 1
            
            print(f"\n[{self.processed_count}/{self.max_pages}] Crawling (Depth {depth}): {current_url}")
            
            # 1. Process and Ingest (Suppress recalc)
            self.mgr.process_url_and_add(current_url, trigger_recalc=False)
            
            # 2. Find more links if depth allows
            if depth < self.max_depth:
                new_links = self.get_links(current_url)
                for link in new_links:
                    if link not in self.visited:
                        self.to_visit.append((link, depth + 1))
            
            # Be polite
            time.sleep(1)

        print("\n🏁 Crawling finished.")
        print(f"   Total pages processed: {self.processed_count}")
        
        # 3. Final Global Recalculation
        print("\n⚡️ Triggering Final Global Network Recalculation...")
        self.mgr.trigger_global_recalculation()
        print("✅ Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TUM Auto Crawler")
    parser.add_argument("url", help="Start URL (e.g., https://www.tum.de/en/)")
    parser.add_argument("--depth", type=int, default=2, help="Max recursion depth")
    parser.add_argument("--limit", type=int, default=20, help="Max pages to crawl")
    
    args = parser.parse_args()
    
    crawler = AutoCrawler(args.url, max_depth=args.depth, max_pages=args.limit)
    crawler.run()
