# Snippet Highlighting 功能快速指南

## 🎯 功能说明

在搜索结果中，关键词会被自动高亮显示，帮助用户快速找到相关信息。

## ✨ 特性

- ✅ 自动提取包含关键词的文本片段
- ✅ 关键词加粗并高亮显示（青色）
- ✅ 保留关键词前后的上下文
- ✅ 支持多关键词同时高亮
- ✅ 智能过滤停用词

## 📖 使用示例

### 搜索查询
用户搜索：`"TUM Computer Science"`

### 搜索结果示例

**原始文本**：
```
The Technical University of Munich (TUM) is a leading research university 
in Germany. The Department of Computer Science at TUM offers world-class 
programs in computer science and engineering.
```

**高亮显示**（关键词以青色加粗显示）：
```
...The Technical University of Munich (**TUM**) is a leading research 
university in Germany. The Department of **Computer Science** at **TUM** 
offers world-class programs in **computer science** and engineering...
```

## 🔧 技术细节

### 后端
- 位置：`search_engine.py`
- 函数：`generate_highlighted_snippet()`
- 返回格式：包含 `[[HIGHLIGHT]]关键词[[/HIGHLIGHT]]` 标记的文本

### 前端
- HTML版本：`static/index.html`
- React版本：`frontend/App.jsx`
- 渲染：将标记转换为 `<strong>` HTML标签

## 🎨 样式

- **字体**：加粗
- **颜色**：青色（cyan-400）
- **背景**：半透明青色背景（cyan-500/20）

## 📝 注意事项

1. 摘要长度默认200字符，可根据需要调整
2. 自动过滤常见停用词（the, a, and等）
3. 关键词匹配不区分大小写
4. 如果文本中没有找到关键词，返回文本开头片段

## 🚀 快速测试

1. 启动后端服务器
2. 在前端搜索框输入关键词（如 "TUM"）
3. 查看搜索结果中的高亮摘要
4. 关键词应该以青色加粗显示
