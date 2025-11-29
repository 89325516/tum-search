# Snippet Highlighting（摘要高亮）功能说明

## 🎯 功能概述

在搜索结果中实现关键词高亮显示，提取包含关键词的文本片段，并将关键词加粗显示，让用户快速找到相关信息。

## ✨ 核心特性

### 1. **智能摘要提取**
- 自动从完整文本中提取包含关键词的片段
- 默认摘要长度：200字符
- 关键词前后自动保留上下文
- 智能添加省略号（...）表示截断

### 2. **多关键词支持**
- 自动识别查询中的多个关键词
- 过滤停用词（the, a, an, and, or等）
- 所有关键词都会被高亮显示

### 3. **高亮显示**
- 关键词以加粗形式显示
- 使用青色（cyan）高亮颜色，符合整体设计风格
- 添加半透明背景，增强视觉效果

## 🔧 技术实现

### 后端实现 (`search_engine.py`)

#### 核心函数

**`generate_highlighted_snippet(text, query, snippet_length=200)`**
- 从文本中提取包含关键词的摘要片段
- 使用特殊标记 `[[HIGHLIGHT]]关键词[[/HIGHLIGHT]]` 包裹关键词
- 返回格式化的摘要字符串

**实现逻辑**：
1. 提取查询中的关键词（过滤停用词）
2. 查找所有关键词在文本中的位置
3. 选择最佳摘要窗口（包含最多关键词）
4. 提取摘要片段并添加省略号
5. 用高亮标记包裹所有关键词

#### 集成到搜索结果

在 `search()` 函数中：
```python
# 获取完整文本
full_text = p.get('full_text', '') or p.get('content', '') or preview

# 生成高亮摘要
highlighted_snippet = generate_highlighted_snippet(
    full_text, 
    query_text, 
    snippet_length=200
)

# 添加到结果中
final_ranked.append({
    ...
    "highlighted_snippet": highlighted_snippet,
    ...
})
```

### 前端实现

#### HTML版本 (`static/index.html`)

```javascript
// 处理高亮摘要
let highlightedSnippet = snippet;
if (item.highlighted_snippet) {
    // 将标记转换为HTML
    highlightedSnippet = item.highlighted_snippet
        .replace(/\[\[HIGHLIGHT\]\](.*?)\[\[\/HIGHLIGHT\]\]/gi, 
                 '<strong class="font-bold text-cyan-400 bg-cyan-500/20 px-1 rounded">$1</strong>');
}

// 使用innerHTML渲染（支持HTML标签）
snippetElement.innerHTML = highlightedSnippet;
```

#### React版本 (`frontend/App.jsx`)

```jsx
<p 
  dangerouslySetInnerHTML={{
    __html: item.highlighted_snippet 
      ? item.highlighted_snippet.replace(
          /\[\[HIGHLIGHT\]\](.*?)\[\[\/HIGHLIGHT\]\]/gi, 
          '<strong class="font-bold text-cyan-400 bg-cyan-500/20 px-1 rounded">$1</strong>'
        )
      : item.content
  }}
/>
```

## 🎨 视觉效果

### 高亮样式
- **字体**：加粗（`font-bold`）
- **颜色**：青色（`text-cyan-400`）
- **背景**：半透明青色（`bg-cyan-500/20`）
- **圆角**：轻微圆角（`rounded`）
- **内边距**：`px-1`（左右各0.25rem）

### 示例效果

```
...The Technical University of Munich (TUM) is one of Europe's leading 
universities in the fields of engineering, technology, medicine, and natural 
sciences. Founded in 1868, TUM has a strong focus on research and innovation...
```

其中 "TUM" 会被高亮显示为：
- **TUM**（加粗、青色、半透明背景）

## 📊 工作流程

```
用户搜索 "TUM Computer Science"
    ↓
后端搜索并获取结果
    ↓
对每个结果：
    1. 提取关键词：["tum", "computer", "science"]
    2. 在文本中查找关键词位置
    3. 提取包含关键词的片段（前后各100字符）
    4. 用[[HIGHLIGHT]]标记包裹关键词
    ↓
返回包含highlighted_snippet的结果
    ↓
前端渲染时：
    1. 解析highlighted_snippet
    2. 将[[HIGHLIGHT]]标记转换为HTML <strong>标签
    3. 应用样式（加粗、青色、背景）
    ↓
用户看到高亮的关键词
```

## 🔍 关键词提取逻辑

### 停用词过滤
自动过滤以下停用词：
- 冠词：the, a, an
- 连词：and, or, but
- 介词：in, on, at, to, for, of, with, by
- 助动词：is, are, was, were
- 疑问词：what, where, when, why, how

### 最小长度
- 关键词最小长度为3个字符
- 过滤掉过短的词

### 不区分大小写
- 关键词匹配不区分大小写
- 保持原文大小写显示

## 📝 使用示例

### 查询：`"TUM Computer Science"`

**原始文本**：
```
The Technical University of Munich (TUM) is a leading research university 
in Germany. The Department of Computer Science at TUM offers world-class 
programs in computer science and engineering. Students can study various 
fields including artificial intelligence, software engineering, and data 
science.
```

**生成的高亮摘要**：
```
...The Technical University of Munich ([[HIGHLIGHT]]TUM[[/HIGHLIGHT]]) is a 
leading research university in Germany. The Department of [[HIGHLIGHT]]Computer 
Science[[/HIGHLIGHT]] at [[HIGHLIGHT]]TUM[[/HIGHLIGHT]] offers world-class 
programs in [[HIGHLIGHT]]computer science[[/HIGHLIGHT]] and engineering...
```

**前端显示**（加粗和青色高亮）：
```
...The Technical University of Munich (TUM) is a leading research university 
in Germany. The Department of Computer Science at TUM offers world-class 
programs in computer science and engineering...
```

## ⚙️ 配置选项

### 摘要长度
默认摘要长度为200字符，可通过参数调整：

```python
highlighted_snippet = generate_highlighted_snippet(
    full_text, 
    query_text, 
    snippet_length=200  # 可调整
)
```

### 停用词列表
可以在 `generate_highlighted_snippet()` 函数中自定义停用词列表。

## 🚀 优势

1. **快速定位**：用户一眼就能看到关键词在结果中的位置
2. **上下文保留**：关键词前后保留足够的上下文信息
3. **多关键词支持**：同时高亮多个相关关键词
4. **视觉突出**：青色加粗样式与整体设计风格一致
5. **智能截断**：自动处理长文本，添加省略号

## 📚 相关文件

- **后端**：`search_engine.py`
  - `generate_highlighted_snippet()` 函数（第48-114行）
  - `search()` 函数中的集成（第202-231行）

- **前端HTML**：`static/index.html`
  - 摘要渲染逻辑（第938-977行）

- **前端React**：`frontend/App.jsx`
  - `ResultCard` 组件中的高亮渲染（第256-265行）

## 🔄 未来优化方向

1. **多片段摘要**：如果关键词在文本中多次出现，可以提取多个片段
2. **句子边界**：在句子边界处截断，避免截断单词
3. **词干提取**：支持词干提取，高亮相关词形变化
4. **短语匹配**：支持多词短语的精确匹配
5. **语言支持**：针对不同语言优化关键词提取
