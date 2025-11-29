#!/usr/bin/env python3
"""
依赖库检查脚本
检查所有必需的依赖库是否已安装
"""
import sys

def check_module(module_name, import_name=None, description=""):
    """检查模块是否可导入"""
    if import_name is None:
        import_name = module_name
    
    try:
        __import__(import_name)
        print(f"✅ {module_name:25s} - {description}")
        return True
    except ImportError:
        print(f"❌ {module_name:25s} - {description} (缺失)")
        return False

def main():
    print("=" * 70)
    print("依赖库检查")
    print("=" * 70)
    print()
    
    # 定义所有需要检查的模块
    modules = [
        # Wiki Dump处理（必需）
        ('mwxml', 'mwxml', 'XML Dump解析库'),
        ('mwparserfromhell', 'mwparserfromhell', 'Wikicode解析库'),
        
        # Web框架（必需）
        ('fastapi', 'fastapi', '异步Web框架'),
        ('uvicorn', 'uvicorn', 'ASGI服务器'),
        ('python-multipart', 'multipart', '文件上传支持'),
        
        # 数据库（必需）
        ('qdrant-client', 'qdrant_client', '向量数据库客户端'),
        
        # 机器学习（必需）
        ('torch', 'torch', 'PyTorch深度学习框架'),
        ('transformers', 'transformers', 'Hugging Face Transformers'),
        ('Pillow', 'PIL', '图像处理库'),
        ('numpy', 'numpy', '数值计算库'),
        ('scipy', 'scipy', '科学计算库'),
        
        # 网络和爬虫
        ('requests', 'requests', 'HTTP请求库'),
        ('beautifulsoup4', 'bs4', 'HTML解析库'),
        ('lxml', 'lxml', 'XML/HTML解析库'),
        ('aiohttp', 'aiohttp', '异步HTTP客户端'),
        ('fake-useragent', 'fake_useragent', 'User-Agent生成'),
        
        # 其他工具
        ('python-dotenv', 'dotenv', '环境变量管理'),
        ('google-generativeai', 'google.generativeai', 'Google Gemini API'),
    ]
    
    # 标准库（应该总是可用）
    stdlib_modules = [
        ('os', 'os', '标准库 - 操作系统接口'),
        ('csv', 'csv', '标准库 - CSV处理'),
        ('bz2', 'bz2', '标准库 - bzip2压缩'),
        ('gzip', 'gzip', '标准库 - gzip压缩'),
        ('tempfile', 'tempfile', '标准库 - 临时文件'),
        ('asyncio', 'asyncio', '标准库 - 异步IO'),
    ]
    
    missing = []
    
    print("📦 第三方依赖库:")
    print("-" * 70)
    for module_name, import_name, desc in modules:
        if not check_module(module_name, import_name, desc):
            missing.append(module_name)
    
    print()
    print("📚 标准库检查:")
    print("-" * 70)
    stdlib_missing = []
    for module_name, import_name, desc in stdlib_modules:
        if not check_module(module_name, import_name, desc):
            stdlib_missing.append(module_name)
    
    print()
    print("=" * 70)
    
    # 总结
    if missing:
        print(f"❌ 发现 {len(missing)} 个缺失的第三方依赖库:")
        for m in missing:
            print(f"   - {m}")
        print()
        print("📥 安装命令:")
        print("   pip install -r requirements.txt")
        print()
        print("   或者单独安装缺失的库:")
        print(f"   pip install {' '.join(missing)}")
        return 1
    elif stdlib_missing:
        print(f"⚠️  警告: {len(stdlib_missing)} 个标准库模块缺失（这不应该发生）:")
        for m in stdlib_missing:
            print(f"   - {m}")
        print()
        print("这可能是Python安装不完整。请重新安装Python。")
        return 1
    else:
        print("✅ 所有依赖库检查通过！")
        print()
        print("🎉 可以正常使用Wiki Dump上传功能了！")
        return 0

if __name__ == '__main__':
    sys.exit(main())
