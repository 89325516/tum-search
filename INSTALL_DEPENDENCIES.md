# 依赖库安装指南

## 📋 完整依赖列表

Wiki Dump上传功能需要的所有依赖库：

### 核心依赖（必需）

```bash
# XML Dump处理
mwxml                    # MediaWiki XML dump解析库
mwparserfromhell        # MediaWiki wikicode解析库

# Web框架
fastapi                 # 异步Web框架
uvicorn                 # ASGI服务器
python-multipart        # 文件上传支持

# 数据库
qdrant-client           # Qdrant向量数据库客户端

# 机器学习
torch                   # PyTorch（CPU版本）
transformers            # Hugging Face Transformers
pillow                  # 图像处理
numpy                   # 数值计算
scipy                   # 科学计算

# 网络和爬虫
requests                # HTTP请求库
beautifulsoup4          # HTML解析
lxml                    # XML/HTML解析
aiohttp                 # 异步HTTP客户端
fake-useragent          # User-Agent生成

# 其他工具
python-dotenv           # 环境变量管理
google-generativeai     # Google Gemini API
maturin                 # Rust构建工具
```

### 标准库（无需安装）

以下库是Python标准库，无需额外安装：
- `os`, `sys`, `csv`, `argparse`, `re`, `typing`
- `collections`, `pathlib`, `datetime`, `time`
- `asyncio`, `io`, `uuid`, `tempfile`
- `bz2`, `gzip` （压缩文件处理）

## 🚀 快速安装

### 方法1: 使用 requirements.txt（推荐）

```bash
# 安装所有依赖
pip install -r requirements.txt
```

### 方法2: 只安装Wiki Dump功能所需依赖

```bash
# 安装Wiki Dump处理所需的最小依赖
pip install mwxml mwparserfromhell fastapi uvicorn python-multipart qdrant-client python-dotenv
```

### 方法3: 使用虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 🔍 验证安装

运行以下命令验证所有依赖是否正确安装：

```bash
python3 -c "
import sys
missing = []
modules = {
    'mwxml': 'XML Dump解析',
    'mwparserfromhell': 'Wikicode解析',
    'fastapi': 'Web框架',
    'uvicorn': 'Web服务器',
    'qdrant_client': '数据库客户端',
    'torch': 'PyTorch',
    'transformers': 'Transformers',
    'bs4': 'BeautifulSoup',
    'dotenv': '环境变量',
}

for module, desc in modules.items():
    try:
        __import__(module)
        print(f'✅ {module:20s} - {desc}')
    except ImportError:
        print(f'❌ {module:20s} - {desc} (缺失)')
        missing.append(module)

if missing:
    print(f'\n❌ 缺失 {len(missing)} 个依赖库')
    print('请运行: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('\n✅ 所有依赖库已正确安装！')
"
```

## 📝 常见问题

### 问题1: mwxml 安装失败

**错误信息**: `ERROR: Could not find a version that satisfies the requirement mwxml`

**解决方案**:
```bash
# 确保pip是最新版本
pip install --upgrade pip

# 尝试从PyPI安装
pip install mwxml

# 如果还是失败，检查Python版本（需要Python 3.7+）
python3 --version
```

### 问题2: torch 安装慢或失败

**解决方案**:
```bash
# 使用CPU版本（更快）
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 或者使用国内镜像
pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题3: 依赖冲突

**解决方案**:
```bash
# 使用虚拟环境隔离依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🔧 Docker环境

如果使用Docker，依赖会在构建时自动安装：

```bash
docker build -t tum-search .
docker run -p 8000:8000 tum-search
```

## 📦 最小化安装

如果只需要Wiki Dump上传功能，最小依赖为：

```bash
pip install \
    mwxml \
    mwparserfromhell \
    fastapi \
    uvicorn \
    python-multipart \
    qdrant-client \
    python-dotenv
```

注意：这将无法使用搜索、图像处理等其他功能。

## ✅ 安装后检查

安装完成后，测试功能是否正常：

```bash
# 1. 检查模块导入
python3 -c "from xml_dump_processor import MediaWikiDumpProcessor; print('✅ XML Dump处理器可用')"

# 2. 检查Web服务器
python3 -c "from web_server import app; print('✅ Web服务器可用')"

# 3. 启动服务器测试
python3 web_server.py --mode user --port 8000
```

如果所有检查都通过，说明依赖安装成功！
