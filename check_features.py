#!/usr/bin/env python3
"""
功能检查脚本 - 检查Graph View和摘要高亮功能是否正确实现
"""
import os
import sys
import re

def check_file(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} 不存在")
        return False

def check_content(filepath, patterns, description):
    """检查文件中是否包含特定内容"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                print(f"✅ {description} - 找到: {pattern}")
            else:
                print(f"❌ {description} - 未找到: {pattern}")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False

def main():
    print("=" * 60)
    print("功能检查：Graph View 和 摘要高亮")
    print("=" * 60)
    print()
    
    issues = []
    
    # 1. 检查前端文件
    print("📄 检查前端文件...")
    static_html = "static/index.html"
    if not check_file(static_html, "前端HTML文件"):
        issues.append("前端HTML文件不存在")
        return
    
    # 2. 检查Graph View功能
    print("\n🔍 检查Graph View功能...")
    graph_patterns = [
        r'tab-graph',
        r'graph-view',
        r'graph-container',
        r'switchTab',
        r'renderGraphView',
        r'/api/search/graph',
        r'echarts'
    ]
    if not check_content(static_html, graph_patterns, "Graph View"):
        issues.append("Graph View功能代码缺失")
    
    # 3. 检查摘要高亮功能
    print("\n🔍 检查摘要高亮功能...")
    highlight_patterns = [
        r'highlighted_snippet',
        r'HIGHLIGHT',
        r'text-cyan-400.*bg-cyan-500'
    ]
    if not check_content(static_html, highlight_patterns, "摘要高亮"):
        issues.append("摘要高亮功能代码缺失")
    
    # 4. 检查后端API
    print("\n🔍 检查后端API...")
    web_server = "web_server.py"
    if check_file(web_server, "后端服务器文件"):
        api_patterns = [
            r'/api/search/graph',
            r'api_search_graph'
        ]
        if not check_content(web_server, api_patterns, "Graph API"):
            issues.append("Graph API缺失")
    
    # 5. 检查搜索引擎
    print("\n🔍 检查搜索引擎...")
    search_engine = "search_engine.py"
    if check_file(search_engine, "搜索引擎文件"):
        engine_patterns = [
            r'generate_highlighted_snippet',
            r'highlighted_snippet.*:'
        ]
        if not check_content(search_engine, engine_patterns, "摘要高亮函数"):
            issues.append("摘要高亮函数缺失")
    
    # 6. 总结
    print("\n" + "=" * 60)
    if issues:
        print("❌ 发现问题：")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 建议：")
        print("  1. 检查代码是否正确提交")
        print("  2. 重启服务器")
        print("  3. 清除浏览器缓存")
        print("  4. 查看 FEATURE_DIAGNOSIS.md 获取详细诊断步骤")
    else:
        print("✅ 所有功能代码检查通过！")
        print("\n💡 如果功能仍不可用，请：")
        print("  1. 重启服务器")
        print("  2. 清除浏览器缓存（Ctrl+Shift+R）")
        print("  3. 使用无痕模式测试")
        print("  4. 查看浏览器控制台是否有错误")
    print("=" * 60)

if __name__ == "__main__":
    main()
