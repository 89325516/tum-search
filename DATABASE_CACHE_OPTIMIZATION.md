# 数据库缓存优化和多Wiki支持

## 🎯 功能概述

实现了智能数据库缓存机制和多Wiki类型支持，大幅提高数据导入和处理效率。

## ✅ 已实现的功能

### 1. **数据库缓存检查** 🚀

在爬取或导入数据前，自动检查数据库中是否已存在该URL的数据，避免重复处理。

**核心功能**：
- ✅ URL存在性检查 (`check_url_exists`)
- ✅ 获取已有数据 (`get_url_from_db`)
- ✅ 批量URL检查 (`batch_check_urls`)
- ✅ 自动跳过已存在的URL

**使用场景**：
- 爬虫递归爬取时自动跳过已爬取的页面
- CSV导入时自动跳过已导入的数据
- XML Dump导入时自动跳过已处理的页面

### 2. **多Wiki类型支持** 🌐

支持多种Wiki格式的XML Dump处理：

**支持的Wiki类型**：
- ✅ **MediaWiki** - 标准MediaWiki格式
- ✅ **Wikipedia** - Wikipedia特定格式（自动检测）
- ✅ **Wikidata** - Wikidata格式（自动检测）
- ✅ **自动检测** - 根据dump文件自动识别类型

**不同Wiki类型的URL格式**：
- MediaWiki: `https://wiki.example.com/Page_Title`
- Wikipedia: `https://en.wikipedia.org/wiki/Page_Title`
- Wikidata: `https://www.wikidata.org/wiki/Q123`

### 3. **智能跳过机制** ⚡

- **爬虫**：爬取前检查数据库，已存在的URL直接跳过
- **CSV导入**：导入前检查数据库，已存在的URL自动跳过
- **XML Dump**：处理时检查数据库，已处理的页面自动跳过

## 📊 性能提升

### 效率提升

- **避免重复爬取**：已存在的URL直接跳过，节省时间和资源
- **减少数据库写入**：只导入新数据，减少I/O操作
- **加快处理速度**：特别是对于大型Wiki站点，效率提升显著

### 统计信息

导入时会显示：
- 总行数/页面数
- 成功导入数
- **跳过数（已存在）** ← 新增
- 失败数
- 晋升到Space R的数量

## 🔧 使用方法

### 爬虫（自动启用）

```python
from system_manager import SystemManager

mgr = SystemManager()

# 自动检查数据库，跳过已存在的URL
mgr.process_url_and_add("https://example.com/page", check_db_first=True)

# 递归爬取，自动跳过已存在的URL
mgr.process_url_recursive("https://example.com", max_depth=3, check_db_first=True)
```

### CSV导入（自动启用）

```python
from csv_importer import CSVImporter

importer = CSVImporter(mgr)

# 自动检查数据库，跳过已存在的URL
stats = importer.import_csv_batch(
    csv_rows,
    check_db_first=True  # 默认True
)
```

### XML Dump处理

```bash
# 自动检测Wiki类型并检查数据库
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://en.wikipedia.org" \
    --import-db \
    --check-db  # 默认启用

# 禁用数据库检查（强制重新导入）
python xml_dump_processor.py wiki_dump.xml \
    --import-db \
    --no-check-db
```

## 🔍 自动检测机制

### Wiki类型自动检测

XML处理器会自动检测dump文件类型：

```python
# 检测逻辑
if "wikipedia" in site_name.lower():
    wiki_type = "wikipedia"
elif "wikidata" in site_name.lower():
    wiki_type = "wikidata"
else:
    wiki_type = "mediawiki"
```

### URL格式自动适配

根据检测到的Wiki类型，自动使用对应的URL格式：

- **Wikipedia**: `{base_url}/wiki/{title}`
- **MediaWiki**: `{base_url}/{title}`
- **Wikidata**: `{base_url}/wiki/{title}`

## 📝 代码实现

### SystemManager新增方法

```python
# 检查URL是否存在
exists = mgr.check_url_exists("https://example.com/page")

# 获取已有数据
data = mgr.get_url_from_db("https://example.com/page")

# 批量检查
urls = ["url1", "url2", "url3"]
results = mgr.batch_check_urls(urls)
```

### 数据库查询优化

使用Qdrant的Filter查询，高效检查URL是否存在：

```python
points, _ = client.scroll(
    collection_name=SPACE_X,
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="url",
                match=models.MatchValue(value=url)
            )
        ]
    ),
    limit=1
)
```

## 🎯 使用场景

### 场景1: 增量导入Wikipedia数据

```bash
# 第一次导入
python xml_dump_processor.py enwiki-latest-pages.xml \
    --base-url "https://en.wikipedia.org" \
    --import-db

# 第二次导入（更新数据）
# 自动跳过已存在的页面，只导入新页面
python xml_dump_processor.py enwiki-latest-pages-new.xml \
    --base-url "https://en.wikipedia.org" \
    --import-db \
    --check-db
```

### 场景2: 递归爬取已爬过的站点

```python
# 如果站点已经部分爬取过
# 新的爬取会自动跳过已存在的页面
mgr.process_url_recursive("https://example.com", max_depth=5, check_db_first=True)
```

### 场景3: CSV批量导入去重

```python
# CSV导入时自动去重
importer.import_csv_file("large_wiki.csv", check_db_first=True)
# 只会导入数据库中不存在的行
```

## 📊 性能对比

### 无缓存检查
- 1000个页面，全部重新爬取
- 处理时间：~10分钟
- 数据库写入：1000次

### 有缓存检查（假设50%已存在）
- 1000个页面，只爬取500个新页面
- 处理时间：~5分钟（节省50%）
- 数据库写入：500次（减少50%）

## ⚙️ 配置选项

### 启用/禁用缓存检查

```python
# 启用（默认）
mgr.process_url_and_add(url, check_db_first=True)

# 禁用（强制重新爬取）
mgr.process_url_and_add(url, check_db_first=False)
```

### CSV导入

```python
# 启用（默认）
importer.import_csv_batch(rows, check_db_first=True)

# 禁用
importer.import_csv_batch(rows, check_db_first=False)
```

## 🔄 工作流程

### 标准流程（启用缓存）

```
URL/数据输入
    ↓
检查数据库
    ├─ 存在 → 跳过，返回已有数据
    └─ 不存在 → 继续处理
        ↓
爬取/解析数据
    ↓
向量化和存储
    ↓
完成
```

### 强制处理流程（禁用缓存）

```
URL/数据输入
    ↓
直接爬取/解析（忽略数据库）
    ↓
向量化和存储（可能覆盖已有数据）
    ↓
完成
```

## 📚 相关文件

- `system_manager.py` - 数据库检查方法
- `csv_importer.py` - CSV导入时的缓存检查
- `xml_dump_processor.py` - XML处理时的缓存检查和Wiki类型检测
- `web_server.py` - 后端API调用

## 🎉 优势总结

1. **效率提升**：避免重复爬取，节省时间和资源
2. **智能适配**：自动检测Wiki类型，使用正确的URL格式
3. **增量更新**：支持增量导入，只处理新数据
4. **灵活控制**：可以启用或禁用缓存检查
5. **统计透明**：清楚显示跳过的数据数量

## 🚀 后续优化

可能的改进方向：
- [ ] URL规范化（处理URL变体，如末尾斜杠）
- [ ] 批量查询优化（一次性查询多个URL）
- [ ] 缓存索引（在内存中维护URL索引）
- [ ] 时间戳比较（根据更新时间决定是否重新爬取）
