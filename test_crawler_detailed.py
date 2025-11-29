#!/usr/bin/env python3
"""
详细测试爬虫 - 带日志输出
"""
import logging
import sys
import traceback

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("🔍 启用详细日志进行测试...\n")

from crawler_v2 import SyncCrawlerWrapper

# 测试一个简单的URL
test_url = "https://httpbin.org/html"  # 简单的HTML页面

print(f"测试URL: {test_url}\n")

try:
    crawler = SyncCrawlerWrapper(
        enable_robots=False,
        enable_content_dedup=False,  # 暂时禁用去重以便测试
        concurrency=1,
        delay=0.5,
        timeout=10,
        verify_ssl=False  # 禁用SSL验证
    )
    
    print("开始解析...\n")
    result = crawler.parse(test_url)
    
    if result:
        print(f"\n✅ 成功!")
        print(f"URL: {result.get('url')}")
        print(f"文本块数: {len(result.get('texts', []))}")
        print(f"链接数: {len(result.get('links', []))}")
        
        if result.get('texts'):
            print(f"\n第一个文本块:")
            print(result.get('texts')[0][:200])
    else:
        print("\n❌ 返回None")
        
except Exception as e:
    print(f"\n❌ 错误: {e}")
    traceback.print_exc()
