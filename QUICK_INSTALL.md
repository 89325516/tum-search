# 快速安装指南

## 🚀 一键安装所有依赖

### 方法1: 使用安装脚本（最简单）

```bash
bash install_deps.sh
```

### 方法2: 手动安装

```bash
pip install -r requirements.txt
```

### 方法3: 验证安装

```bash
python3 check_dependencies.py
```

## ⚡ 只安装Wiki Dump功能所需依赖

如果您只需要Wiki Dump上传功能，可以只安装最小依赖：

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

## 🔍 检查缺失的依赖

运行依赖检查脚本：

```bash
python3 check_dependencies.py
```

脚本会列出所有缺失的依赖库，并提示安装命令。

## ❌ 如果安装失败

### 问题1: mwxml安装失败

```bash
# 确保pip是最新的
pip install --upgrade pip

# 单独安装
pip install mwxml mwparserfromhell
```

### 问题2: 权限错误

```bash
# 使用用户安装
pip install --user -r requirements.txt
```

### 问题3: 使用虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

## ✅ 安装成功验证

安装完成后，测试功能：

```bash
# 1. 检查模块导入
python3 -c "from xml_dump_processor import MediaWikiDumpProcessor; print('✅ 成功')"

# 2. 启动服务器
python3 web_server.py --mode user --port 8000
```

## 📚 更多信息

- 完整安装指南: `INSTALL_DEPENDENCIES.md`
- 依赖检查脚本: `check_dependencies.py`
- 安装脚本: `install_deps.sh`
