# CSV批量导入功能

## 📋 功能说明

添加了CSV批量导入功能，可以将类似Wiki网站的数据直接从CSV文件批量导入到数据库中，避免重复爬取，极大提高数据导入效率。

## ✅ 已实现的功能

### 1. CSV解析和导入
- ✅ 支持多种CSV格式（UTF-8、Latin-1编码）
- ✅ 自动识别CSV列（title, content, url, category等）
- ✅ 智能字段匹配（不区分大小写）
- ✅ 自动生成URL（如果CSV中没有URL列）

### 2. 批量处理
- ✅ 批量向量化和存储（默认每批50条）
- ✅ 自动独特性检测和晋升到Space R
- ✅ 进度反馈（实时显示导入进度）

### 3. 前端界面
- ✅ CSV文件选择器
- ✅ 密码验证（与URL爬取共用密码）
- ✅ URL前缀配置（可选）
- ✅ 上传状态反馈

### 4. 后端处理
- ✅ 异步后台处理（不阻塞请求）
- ✅ WebSocket实时进度推送
- ✅ 错误处理和日志记录
- ✅ 自动清理临时文件

## 🎯 使用方法

### 步骤 1: 准备CSV文件

CSV文件应包含以下列（列名不区分大小写）：

**必需列：**
- `content` / `text` / `body` - 内容文本

**可选列：**
- `title` / `name` / `page` - 标题
- `url` / `link` - URL链接
- `category` / `type` - 分类

**CSV示例：**

```csv
title,content,url,category
"Machine Learning","Machine learning is a subset of artificial intelligence...","https://wiki.example.com/ml","Technology"
"Deep Learning","Deep learning uses neural networks...","https://wiki.example.com/deep-learning","Technology"
"Python Programming","Python is a high-level programming language...","https://wiki.example.com/python","Programming"
```

或者更简单的格式：

```csv
title,content
"Article 1","This is the content of article 1..."
"Article 2","This is the content of article 2..."
```

如果没有URL列，系统会自动生成URL（基于URL前缀和标题）。

### 步骤 2: 上传CSV文件

1. 在前端页面找到"Batch Import (Wiki Style)"区域
2. 点击"选择文件"按钮，选择CSV文件
3. 可选：输入URL前缀（例如：`https://wiki.example.com/page`）
4. 输入密码（与URL爬取相同的密码）
5. 点击"批量导入"按钮

### 步骤 3: 查看导入进度

导入过程中，您会看到：
- 实时进度提示（通过WebSocket推送）
- 成功/失败统计
- 自动晋升到Space R的内容数量

## 📊 CSV格式说明

### 支持的列名（不区分大小写）

**内容列**（优先级从高到低）：
- `content`
- `text`
- `body`
- `description`
- `abstract`

如果以上列都不存在，系统会尝试组合所有非URL/标题列作为内容。

**标题列**（优先级从高到低）：
- `title`
- `name`
- `page`

**URL列**（优先级从高到低）：
- `url`
- `link`
- `href`

如果CSV中没有URL列，系统会根据以下规则生成：
- 如果提供了URL前缀：`{url_prefix}/{title_with_underscores}`
- 如果没有URL前缀：`csv_import/{title_with_underscores}` 或 `csv_import/{random_id}`

**分类列**：
- `category`
- `type`

### 数据要求

- 内容文本长度至少10个字符（太短的会被跳过）
- 支持多行文本（CSV格式中的换行符会被保留）
- 自动清理空值和多余空格

## 🔧 配置说明

### 环境变量

CSV导入功能使用与URL爬取相同的密码验证：
- `CRAWL_PASSWORD` - 在 `.env` 文件中设置

### 导入参数

- **批量大小**：默认50条/批（可在代码中调整）
- **独特性检测**：默认开启，独特内容会自动晋升到Space R
- **URL前缀**：可选，用于生成缺失的URL

## 📝 导入统计

导入完成后，系统会返回统计信息：

```json
{
  "total": 100,        // 总行数
  "processed": 100,    // 已处理行数
  "success": 95,       // 成功导入数
  "failed": 5,         // 失败数
  "promoted": 10       // 晋升到Space R的数量
}
```

## 🔍 错误处理

### 常见错误

1. **密码错误**
   - 错误信息：`密码错误，CSV导入被拒绝`
   - 解决：检查密码是否正确

2. **文件格式错误**
   - 错误信息：`只支持CSV文件格式`
   - 解决：确保文件扩展名为`.csv`

3. **编码问题**
   - 系统会自动尝试多种编码（UTF-8、Latin-1）
   - 如果仍有问题，请将CSV文件转换为UTF-8编码

4. **内容太短**
   - 内容少于10个字符的行会被跳过
   - 确保每行都有足够的内容

## 💡 使用建议

### 性能优化

1. **批量大小**
   - 默认50条/批，适合大多数情况
   - 对于大型CSV（>1000行），可以增加到100

2. **URL前缀**
   - 建议为不同来源的Wiki设置不同的URL前缀
   - 例如：`https://wiki.example.com/page`、`https://docs.example.com/article`

3. **分类标签**
   - 使用`category`列可以帮助后续搜索和过滤
   - 统一的分类命名有助于数据管理

### 数据质量

1. **内容清理**
   - 导入前建议清理HTML标签（如果CSV中包含）
   - 确保内容是可读的纯文本

2. **标题质量**
   - 良好的标题有助于生成有意义的URL
   - 标题应该是简洁、描述性的

3. **URL唯一性**
   - 如果CSV中有URL列，确保URL是唯一的
   - 重复的URL可能导致数据覆盖

## 🔒 安全说明

- CSV导入需要密码验证（与URL爬取共用）
- 文件上传后存储在临时目录，处理完成后自动删除
- 建议在生产环境中使用HTTPS

## 📚 相关文件

- `csv_importer.py` - CSV导入核心模块
- `web_server.py` - API端点和后台任务
- `static/index.html` - 前端上传界面
- `system_manager.py` - 数据库存储逻辑

## 🔄 更新日志

### v1.0 (当前版本)
- ✅ 支持多种CSV格式和列名
- ✅ 批量导入和进度反馈
- ✅ 自动独特性检测和晋升
- ✅ 密码验证和安全控制
- ✅ 前端上传界面

## 🚀 后续改进

可能的改进方向：
- [ ] 支持Excel文件导入（.xlsx）
- [ ] 支持JSON格式导入
- [ ] 导入预览功能（上传前预览前几行）
- [ ] 导入历史记录
- [ ] 重复数据检测和去重
- [ ] 自定义字段映射配置
