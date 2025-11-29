# 运行库依赖问题修复总结

## ✅ 已完成的修复

### 1. requirements.txt 检查
- ✅ 已确认包含所有必需的依赖库
- ✅ `mwxml` 和 `mwparserfromhell` 已在列表中（第18-19行）

### 2. 创建的辅助工具

#### ✅ 依赖检查脚本 (`check_dependencies.py`)
- 自动检查所有依赖库是否已安装
- 显示缺失的依赖库
- 提供安装命令

#### ✅ 一键安装脚本 (`install_deps.sh`)
- 自动升级pip
- 从requirements.txt安装所有依赖
- 自动检查安装结果

### 3. 创建的文档

#### ✅ 详细安装指南 (`INSTALL_DEPENDENCIES.md`)
- 完整的依赖列表
- 安装方法说明
- 常见问题解决方案
- 验证方法

#### ✅ 快速安装指南 (`QUICK_INSTALL.md`)
- 简化版安装说明
- 快速命令参考

#### ✅ README.md 更新
- 添加了安装说明
- 包含多种安装方法
- 添加了依赖检查步骤

## 🔧 如何修复依赖问题

### 方法1: 使用一键安装脚本（推荐）

```bash
bash install_deps.sh
```

### 方法2: 手动安装所有依赖

```bash
pip install -r requirements.txt
```

### 方法3: 只安装缺失的依赖

```bash
pip install mwxml mwparserfromhell
```

### 方法4: 使用虚拟环境（推荐用于生产环境）

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

## 🔍 验证依赖是否安装成功

运行检查脚本：

```bash
python3 check_dependencies.py
```

**期望输出**：
```
✅ mwxml                     - XML Dump解析库
✅ mwparserfromhell          - Wikicode解析库
...
✅ 所有依赖库检查通过！
```

## 📋 当前依赖状态

### ✅ 已在 requirements.txt 中的依赖

所有必需依赖都已列出：
- `mwxml` ✅
- `mwparserfromhell` ✅
- `fastapi`, `uvicorn`, `python-multipart` ✅
- `qdrant-client` ✅
- `torch`, `transformers` ✅
- 其他所有依赖 ✅

### ⚠️ 需要安装的依赖

如果运行 `check_dependencies.py` 显示缺失，请安装：

```bash
# 如果只缺失Wiki Dump相关依赖
pip install mwxml mwparserfromhell

# 如果缺失多个依赖
pip install -r requirements.txt
```

## 🚀 使用步骤

### 首次安装

1. **检查当前状态**
   ```bash
   python3 check_dependencies.py
   ```

2. **安装缺失的依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **再次检查**
   ```bash
   python3 check_dependencies.py
   ```

4. **测试功能**
   ```bash
   python3 -c "from xml_dump_processor import MediaWikiDumpProcessor; print('✅ 成功')"
   ```

### 日常使用

如果只是更新依赖：
```bash
pip install --upgrade -r requirements.txt
```

## 📝 依赖库列表

### Wiki Dump功能必需
- `mwxml` - MediaWiki XML dump解析
- `mwparserfromhell` - MediaWiki wikicode解析

### Web服务器必需
- `fastapi` - Web框架
- `uvicorn` - ASGI服务器
- `python-multipart` - 文件上传

### 数据库必需
- `qdrant-client` - Qdrant向量数据库客户端

### 其他功能
- 完整的依赖列表请查看 `requirements.txt`

## ❌ 常见问题

### 问题1: pip install 失败

**解决方案**:
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像（如果网络慢）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2: 权限错误

**解决方案**:
```bash
# 使用用户安装
pip install --user -r requirements.txt

# 或使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 问题3: 依赖冲突

**解决方案**:
```bash
# 使用虚拟环境隔离
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✅ 修复验证

修复完成后，运行以下命令验证：

```bash
# 1. 检查依赖
python3 check_dependencies.py

# 2. 测试导入
python3 -c "from xml_dump_processor import MediaWikiDumpProcessor; print('✅ XML处理器可用')"

# 3. 启动服务器
python3 web_server.py --mode user --port 8000
```

如果所有步骤都成功，说明依赖问题已完全解决！

## 📚 相关文档

- `INSTALL_DEPENDENCIES.md` - 详细安装指南
- `QUICK_INSTALL.md` - 快速安装指南
- `requirements.txt` - 完整依赖列表
- `check_dependencies.py` - 依赖检查脚本
- `install_deps.sh` - 一键安装脚本
