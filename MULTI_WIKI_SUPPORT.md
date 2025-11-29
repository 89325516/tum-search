# 多Wiki类型支持文档

## 🎯 支持的Wiki类型

XML Dump处理工具现在支持多种Wiki格式：

### 1. **MediaWiki**（标准格式）

标准MediaWiki站点，如企业内部Wiki。

**URL格式**：`https://wiki.example.com/Page_Title`

**特征**：
- 标准的MediaWiki XML dump格式
- 标准的wikicode语法
- 可配置的命名空间

### 2. **Wikipedia**

Wikipedia系列站点（en.wikipedia.org, zh.wikipedia.org等）

**URL格式**：`https://en.wikipedia.org/wiki/Page_Title`

**特征**：
- 使用`/wiki/`路径前缀
- 自动检测Wikipedia标识
- 跳过User、Talk、Portal等命名空间

### 3. **Wikidata**

Wikidata知识库

**URL格式**：`https://www.wikidata.org/wiki/Q123`

**特征**：
- 支持Q/P编号的实体
- 特殊的链接格式
- 自动识别Wikidata dump

## 🔍 自动检测机制

处理器会根据dump文件中的站点信息自动检测Wiki类型：

```python
# 检测逻辑
if "wikipedia" in site_name.lower() or "wikipedia" in db_name.lower():
    wiki_type = "wikipedia"
elif "wikidata" in site_name.lower() or "wikidata" in db_name.lower():
    wiki_type = "wikidata"
else:
    wiki_type = "mediawiki"
```

## 📝 使用方法

### 基本用法（自动检测）

```bash
# 自动检测Wikipedia类型
python xml_dump_processor.py enwiki-latest-pages.xml \
    --base-url "https://en.wikipedia.org" \
    --import-db

# 自动检测MediaWiki类型
python xml_dump_processor.py company_wiki.xml \
    --base-url "https://wiki.company.com" \
    --import-db
```

### 指定Wiki类型（高级用法）

```bash
# 强制使用Wikipedia格式
python xml_dump_processor.py dump.xml \
    --base-url "https://wiki.example.com" \
    --wiki-type wikipedia
```

## 🔧 Wiki配置

每种Wiki类型都有特定的配置：

### Wikipedia配置

```python
{
    "url_pattern": "{base_url}/wiki/{title}",
    "skip_namespaces": {'File', 'Image', 'Category', 'Template', 'Media', 'User', 'Talk', 'Help', 'Portal'},
    "link_patterns": [r'\[\[([^\]]+)\]\]']
}
```

### MediaWiki配置

```python
{
    "url_pattern": "{base_url}/{title}",
    "skip_namespaces": {'File', 'Image', 'Category', 'Template', 'Media'},
    "link_patterns": [r'\[\[([^\]]+)\]\]']
}
```

### Wikidata配置

```python
{
    "url_pattern": "{base_url}/wiki/{title}",
    "skip_namespaces": {'Property', 'Property talk', 'Item', 'Item talk'},
    "link_patterns": [r'\[\[([^\]]+)\]\]', r'Q\d+', r'P\d+']
}
```

## ✅ 自动适配功能

- ✅ **URL格式自动适配**：根据Wiki类型使用正确的URL格式
- ✅ **命名空间过滤**：自动跳过不相关的命名空间
- ✅ **链接提取优化**：针对不同Wiki类型的链接格式优化
- ✅ **内容清理**：适配不同Wiki的wikicode格式

## 📊 使用示例

### Wikipedia数据导入

```bash
# 下载Wikipedia dump
wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2

# 解压
bunzip2 enwiki-latest-pages-articles.xml.bz2

# 处理并导入
python xml_dump_processor.py enwiki-latest-pages-articles.xml \
    --base-url "https://en.wikipedia.org" \
    --import-db \
    --import-edges \
    --batch-size 100
```

### MediaWiki数据导入

```bash
# 从MediaWiki站点导出dump
# Special:Export → 导出所有页面

# 处理并导入
python xml_dump_processor.py mediawiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --import-db
```

## 🔄 工作流程

```
XML Dump文件
    ↓
读取站点信息
    ↓
自动检测Wiki类型
    ├─ Wikipedia → 使用Wikipedia配置
    ├─ Wikidata → 使用Wikidata配置
    └─ 其他 → 使用MediaWiki配置
    ↓
应用URL格式和命名空间过滤
    ↓
处理页面和链接
    ↓
生成CSV或导入数据库
```

## 💡 最佳实践

1. **使用自动检测**：大多数情况下，自动检测已经足够
2. **指定base-url**：确保URL格式正确
3. **启用数据库检查**：避免重复导入
4. **批量导入**：使用合适的batch-size提高效率

## 📚 相关文档

- `XML_DUMP_PROCESSOR_GUIDE.md` - 完整使用指南
- `DATABASE_CACHE_OPTIMIZATION.md` - 数据库缓存优化说明
