# MediaWiki XML Dump 处理工具使用指南

## 📋 功能说明

这是一个专门用于处理MediaWiki XML Dump文件的工具，可以：

1. **解析XML Dump**：使用`mwxml`库高效解析大型MediaWiki XML dump文件
2. **提取页面数据**：从XML中提取页面标题、内容、URL等信息
3. **提取链接关系**：从wikicode中解析内部链接，构建页面之间的关系图
4. **生成CSV文件**：生成节点CSV（页面数据）和边CSV（链接关系）
5. **一键导入数据库**：直接导入到Qdrant数据库和InteractionManager

## 🚀 快速开始

### 步骤 1: 安装依赖

```bash
pip install mwxml mwparserfromhell
```

或者安装所有依赖：

```bash
pip install -r requirements.txt
```

### 步骤 2: 准备XML Dump文件

从MediaWiki站点下载XML dump文件（通常从`Special:Export`页面导出）。

示例文件名：`wiki_dump.xml`

### 步骤 3: 运行处理工具

#### 基础用法（只生成CSV）

```bash
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --output-dir ./output
```

#### 一键导入数据库

```bash
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --import-db \
    --import-edges
```

#### 测试模式（只处理前100个页面）

```bash
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --max-pages 100 \
    --output-dir ./test_output
```

## 📊 输出文件

### 节点CSV (`wiki_nodes.csv`)

包含所有页面的基本信息：

```csv
title,content,url,category
"Machine Learning","Machine learning is a subset...","https://wiki.example.com/Machine_Learning","Wiki"
"Deep Learning","Deep learning uses neural...","https://wiki.example.com/Deep_Learning","Wiki"
```

**字段说明**：
- `title`: 页面标题
- `content`: 页面纯文本内容（已清理wikicode标记）
- `url`: 页面完整URL
- `category`: 页面分类（默认"Wiki"）

### 边CSV (`wiki_edges.csv`)

包含页面之间的链接关系：

```csv
source_title,target_title
"Machine Learning","Deep Learning"
"Machine Learning","Neural Networks"
"Python Programming","Data Science"
```

**字段说明**：
- `source_title`: 源页面标题
- `target_title`: 目标页面标题（链接指向的页面）

## 🔧 命令行参数

### 必需参数

- `dump_file`: MediaWiki XML dump文件路径

### 可选参数

- `--base-url`: Wiki基础URL（例如: `https://wiki.example.com`）
- `--output-dir`: 输出目录（默认: 当前目录）
- `--nodes-csv`: 节点CSV文件名（默认: `wiki_nodes.csv`）
- `--edges-csv`: 边CSV文件名（默认: `wiki_edges.csv`）
- `--max-pages`: 最大处理页面数（用于测试，默认: 处理所有）
- `--import-db`: 一键导入到数据库
- `--import-edges`: 同时导入边（链接关系）到InteractionManager
- `--url-prefix`: 数据库导入时的URL前缀（覆盖base-url）
- `--batch-size`: 数据库批量导入大小（默认: 50）

## 📝 使用示例

### 示例 1: 完整处理流程

```bash
# 1. 生成CSV文件
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --output-dir ./wiki_data

# 2. 检查CSV文件
head -5 ./wiki_data/wiki_nodes.csv
head -5 ./wiki_data/wiki_edges.csv

# 3. 手动导入（使用CSV导入工具）
python -c "from csv_importer import CSVImporter; from system_manager import SystemManager; ..."
```

### 示例 2: 一键导入

```bash
# 直接导入到数据库，包括边
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --import-db \
    --import-edges \
    --batch-size 100
```

### 示例 3: 只导入边（如果节点已存在）

```bash
# 如果节点已经导入，只需要导入边
python import_edges.py wiki_edges.csv
```

## 🔍 工作原理

### 1. XML解析

使用`mwxml`库流式解析XML文件，支持处理大型dump文件：

```python
dump = mwxml.Dump.from_file(file)
for page in dump:
    for revision in page:
        # 处理每个页面的最新版本
```

### 2. 链接提取

从MediaWiki wikicode中提取内部链接：

- 支持标准链接格式：`[[Page Title]]`
- 支持带显示文本：`[[Page Title|Display Text]]`
- 自动跳过特殊命名空间（File、Image、Category等）
- 规范化标题处理

### 3. 文本提取

从wikicode中提取纯文本：

- 使用`mwparserfromhell`解析wikicode
- 移除所有wikicode标记
- 保留可读的纯文本内容

### 4. 数据库导入

- 节点导入：使用`CSVImporter`批量导入页面
- 边导入：使用`import_edges.py`导入链接关系到`InteractionManager`

## ⚙️ 高级配置

### 命名空间过滤

默认只处理主命名空间（0）。可以在代码中修改：

```python
processor = MediaWikiDumpProcessor(
    base_url="https://wiki.example.com",
    namespace_filter={0, 1}  # 处理主命名空间和讨论页
)
```

### 链接提取策略

系统会：

1. 首先尝试使用`mwparserfromhell`解析wikicode
2. 如果失败，使用正则表达式作为后备方案
3. 自动跳过外部链接、文件链接、模板等

### 内容过滤

只有内容长度超过50字符的页面才会被导入（可在代码中调整）。

## 🔒 注意事项

### 内存使用

- 大型dump文件可能占用大量内存
- 建议使用`--max-pages`参数先测试
- 或者分批处理dump文件

### 处理时间

- 处理速度取决于XML文件大小和系统性能
- 大型dump（>10GB）可能需要数小时
- 使用进度回调监控处理状态

### 数据完整性

- 边导入需要节点已经存在于数据库中
- 建议先导入节点，再导入边
- 或者使用`--import-db --import-edges`同时导入

## 🐛 故障排除

### 问题 1: 导入失败 "缺少依赖库"

**解决**：
```bash
pip install mwxml mwparserfromhell
```

### 问题 2: 内存不足

**解决**：
- 使用`--max-pages`限制处理数量
- 分批处理dump文件
- 增加系统内存

### 问题 3: 边导入失败

**解决**：
- 确保节点已经导入到数据库
- 检查边的CSV格式是否正确
- 查看标题映射是否匹配

### 问题 4: 编码错误

**解决**：
- XML文件应为UTF-8编码
- 如果遇到编码问题，尝试转换文件编码：
```bash
iconv -f ISO-8859-1 -t UTF-8 input.xml > output.xml
```

## 📚 相关文件

- `xml_dump_processor.py` - 主处理脚本
- `import_edges.py` - 边导入工具
- `csv_importer.py` - CSV导入模块
- `system_manager.py` - 数据库管理
- `interaction_manager.py` - 链接关系管理

## 🔄 工作流程

```
XML Dump文件
    ↓
解析XML (mwxml)
    ↓
提取页面数据
    ↓
提取wikicode链接
    ↓
生成节点CSV + 边CSV
    ↓
[可选] 导入到数据库
    ├─ 节点 → Qdrant (CSV Importer)
    └─ 边 → InteractionManager
```

## ✅ 特性总结

- ✅ 流式处理，支持大型XML文件
- ✅ 智能链接提取（wikicode解析）
- ✅ 自动文本清理（移除wikicode标记）
- ✅ 批量导入（提高效率）
- ✅ 一键导入功能（简化操作）
- ✅ 进度反馈（实时监控）
- ✅ 错误处理（完善的异常处理）

## 🎯 使用建议

1. **首次使用**：先用`--max-pages 100`测试
2. **生产使用**：处理完整dump后再导入
3. **性能优化**：调整`--batch-size`参数
4. **数据验证**：导入后检查数据库中的数据完整性

## 📞 获取帮助

```bash
python xml_dump_processor.py --help
```
