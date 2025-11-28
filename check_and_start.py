#!/usr/bin/env python3
"""检查依赖并尝试启动服务器"""
import sys
import os

print("=" * 60)
print("🔍 检查依赖和配置...")
print("=" * 60)

# 检查Python版本
print(f"Python 版本: {sys.version}")

# 检查基本依赖
missing_modules = []
modules_to_check = [
    ('fastapi', 'FastAPI'),
    ('uvicorn', 'Uvicorn'),
    ('qdrant_client', 'Qdrant Client'),
    ('dotenv', 'python-dotenv'),
]

for module_name, display_name in modules_to_check:
    try:
        __import__(module_name)
        print(f"✅ {display_name}: 已安装")
    except ImportError:
        print(f"❌ {display_name}: 未安装")
        missing_modules.append(module_name)

# 检查环境变量
print("\n" + "=" * 60)
print("🔐 检查环境变量...")
print("=" * 60)

env_file = '.env'
if os.path.exists(env_file):
    print(f"✅ .env 文件存在")
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['QDRANT_URL', 'QDRANT_API_KEY']
    optional_vars = ['GOOGLE_API_KEY']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: 已设置 ({'*' * min(10, len(value))})")
        else:
            print(f"❌ {var}: 未设置")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: 已设置")
        else:
            print(f"⚠️  {var}: 未设置（可选，摘要功能将不可用）")
else:
    print(f"❌ .env 文件不存在")

# 总结
print("\n" + "=" * 60)
print("📊 总结")
print("=" * 60)

if missing_modules:
    print(f"❌ 缺少以下模块: {', '.join(missing_modules)}")
    print(f"\n请运行: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("✅ 所有依赖都已安装")
    
    if not os.path.exists(env_file):
        print("⚠️  警告: .env 文件不存在，某些功能可能无法正常工作")
        print("   创建 .env 文件并设置 QDRANT_URL 和 QDRANT_API_KEY")
    
    print("\n🚀 可以尝试启动服务器:")
    print("   python3 web_server.py --mode user --port 8000")
