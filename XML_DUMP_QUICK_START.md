# XML Dump 处理工具快速开始

## 🚀 一键使用

### 完整流程（推荐）

```bash
# 1. 安装依赖
pip install mwxml mwparserfromhell

# 2. 处理XML dump并一键导入
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --import-db \
    --import-edges
```

### 分步操作

```bash
# 步骤1: 生成CSV文件
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --output-dir ./output

# 步骤2: 导入节点（使用CSV导入功能）
# 通过前端界面上传 wiki_nodes.csv

# 步骤3: 导入边（可选）
python import_edges.py output/wiki_edges.csv \
    --base-url "https://wiki.example.com"
```

## 📝 CSV格式

### 节点CSV (`wiki_nodes.csv`)
```csv
title,content,url,category
"Page Title","Page content here...","https://wiki.example.com/Page_Title","Wiki"
```

### 边CSV (`wiki_edges.csv`)
```csv
source_title,target_title
"Page A","Page B"
"Page A","Page C"
```

## 🔧 常用命令

### 测试模式（处理前100个页面）
```bash
python xml_dump_processor.py wiki_dump.xml \
    --max-pages 100 \
    --base-url "https://wiki.example.com"
```

### 只生成CSV，不导入
```bash
python xml_dump_processor.py wiki_dump.xml \
    --base-url "https://wiki.example.com" \
    --output-dir ./csv_output
```

### 只导入边（节点已存在）
```bash
python import_edges.py wiki_edges.csv \
    --base-url "https://wiki.example.com"
```

## ✅ 完整功能列表

- ✅ XML Dump解析（使用mwxml）
- ✅ 节点提取（页面标题、内容、URL）
- ✅ 链接提取（从wikicode解析内部链接）
- ✅ CSV生成（节点CSV + 边CSV）
- ✅ 一键导入（节点 + 边）
- ✅ 批量处理（支持大型dump文件）
- ✅ 进度反馈（实时显示处理状态）

## 📚 详细文档

完整使用文档请参考：`XML_DUMP_PROCESSOR_GUIDE.md`
