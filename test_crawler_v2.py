#!/usr/bin/env python3
"""
测试新爬虫功能
"""
import sys
import traceback
import time
from crawler_v2 import SyncCrawlerWrapper

def test_crawler():
    print("=" * 60)
    print("🧪 测试新爬虫 (crawler_v2)")
    print("=" * 60)
    
    # 测试1: 创建爬虫实例
    print("\n[测试1] 创建爬虫实例...")
    try:
        crawler = SyncCrawlerWrapper(
            enable_robots=False,  # 禁用robots.txt以便测试
            enable_content_dedup=True,
            concurrency=2,
            delay=1.0,
            timeout=10
        )
        print("✅ 爬虫实例创建成功")
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试2: 测试解析一个真实URL
    print("\n[测试2] 测试解析URL (https://www.tum.de/en/)...")
    test_url = "https://www.tum.de/en/"
    
    try:
        start_time = time.time()
        print(f"   开始爬取: {test_url}")
        result = crawler.parse(test_url)
        elapsed = time.time() - start_time
        
        if result:
            print(f"✅ 解析成功 (耗时: {elapsed:.2f}秒)")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   文本块数: {len(result.get('texts', []))}")
            print(f"   链接数: {len(result.get('links', []))}")
            print(f"   图片数: {len(result.get('images', []))}")
            
            # 显示前几个文本块
            texts = result.get('texts', [])
            if texts:
                print(f"\n   前3个文本块预览:")
                for i, text in enumerate(texts[:3], 1):
                    preview = text[:100].replace('\n', ' ')
                    print(f"   [{i}] {preview}...")
            
            return True
        else:
            print(f"⚠️  解析返回None (耗时: {elapsed:.2f}秒)")
            print("   可能原因:")
            print("   - 网站内容被过滤（熵值检查）")
            print("   - 网络请求失败")
            print("   - robots.txt阻止")
            return False
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        traceback.print_exc()
        return False

def test_system_manager():
    print("\n" + "=" * 60)
    print("🧪 测试SystemManager中的爬虫")
    print("=" * 60)
    
    try:
        print("\n[测试] 导入SystemManager...")
        from system_manager import SystemManager
        print("✅ SystemManager导入成功")
        
        print("\n[测试] 创建SystemManager实例...")
        # 注意：这会初始化数据库连接等，可能需要一些时间
        mgr = SystemManager()
        print("✅ SystemManager实例创建成功")
        
        print(f"\n   爬虫类型: {type(mgr.crawler).__name__}")
        if hasattr(mgr.crawler, 'async_crawler'):
            print(f"   内部爬虫: AsyncCrawler")
        else:
            print(f"   内部爬虫: SmartCrawler (旧版)")
        
        return True
        
    except Exception as e:
        print(f"❌ SystemManager测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 开始测试...\n")
    
    # 测试1: 直接测试爬虫
    test1_result = test_crawler()
    
    # 测试2: 测试SystemManager中的爬虫
    test2_result = test_system_manager()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"爬虫功能测试: {'✅ 通过' if test1_result else '⚠️  需要检查'}")
    print(f"SystemManager测试: {'✅ 通过' if test2_result else '❌ 失败'}")
    
    if test1_result and test2_result:
        print("\n✅ 所有测试通过！新爬虫可以正常使用。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试未通过，请检查上述输出。")
        sys.exit(1)
