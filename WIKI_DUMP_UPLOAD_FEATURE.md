# Wiki Dump 上传功能

## 🎯 功能说明

现在您可以直接通过网页界面上传 Wiki XML Dump 文件，系统会自动解析并导入到数据库，**无需借助爬虫**！

### 支持的功能

- ✅ **直接上传XML Dump文件**：支持 `.xml`、`.xml.bz2`、`.xml.gz` 格式
- ✅ **自动解析**：自动检测Wiki类型（MediaWiki/Wikipedia/Wikidata）
- ✅ **批量导入**：自动导入所有页面到数据库
- ✅ **链接关系导入**：自动导入页面之间的链接关系（边）
- ✅ **数据库缓存**：自动跳过已存在的URL，提高效率
- ✅ **进度显示**：实时显示处理进度

## 🚀 使用方法

### 步骤 1: 访问上传界面

1. 启动服务器：
   ```bash
   python3 web_server.py --mode user --port 8000
   ```

2. 打开浏览器访问：`http://localhost:8000/`

3. 找到 **"Wiki Dump Import"** 部分（紫色标签）

### 步骤 2: 准备XML Dump文件

获取Wiki的XML Dump文件：

- **Wikipedia**: 从 [dumps.wikimedia.org](https://dumps.wikimedia.org/) 下载
- **MediaWiki站点**: 从 `Special:Export` 页面导出
- **其他Wiki**: 使用MediaWiki的导出功能

支持的文件格式：
- `.xml` - 未压缩的XML文件
- `.xml.bz2` - bzip2压缩的XML文件
- `.xml.gz` - gzip压缩的XML文件

### 步骤 3: 填写上传信息

在 "Wiki Dump Import" 区域：

1. **选择文件**：点击"选择文件"按钮，选择您的XML Dump文件
2. **Wiki基础URL**（可选）：
   - 例如：`https://en.wikipedia.org`
   - 例如：`https://wiki.example.com`
   - 如果不填写，系统会从dump文件中自动检测
3. **最大页面数**（可选）：
   - 用于测试，限制处理的页面数量
   - 例如：输入 `100` 只处理前100个页面
   - 留空则处理所有页面
4. **密码**：输入配置的爬取密码

### 步骤 4: 上传并等待

1. 点击 **"导入Dump"** 按钮
2. 文件开始上传到服务器
3. 系统开始后台处理：
   - 解析XML Dump文件
   - 提取页面内容和链接关系
   - 导入到数据库
   - 导入链接关系（边）

4. 通过WebSocket实时查看进度：
   - 处理进度百分比
   - 当前处理的页面
   - 导入状态

### 步骤 5: 查看结果

处理完成后，您会看到通知消息，包含：

- ✅ 处理页面数
- ✅ 成功导入数量
- ✅ 跳过（已存在）数量
- ✅ 链接关系数量
- ✅ 处理时间

## 📋 使用示例

### 示例 1: 导入Wikipedia Dump

```
文件: enwiki-latest-pages-articles.xml.bz2
Wiki基础URL: https://en.wikipedia.org
最大页面数: (留空，处理全部)
密码: your-password
```

### 示例 2: 测试导入（小批量）

```
文件: small_wiki_dump.xml
Wiki基础URL: https://wiki.example.com
最大页面数: 100
密码: your-password
```

### 示例 3: 导入MediaWiki站点

```
文件: company_wiki.xml.gz
Wiki基础URL: https://wiki.company.com
最大页面数: (留空)
密码: your-password
```

## 🔍 技术细节

### 处理流程

1. **文件上传**：XML Dump文件保存到临时目录
2. **解析XML**：使用 `mwxml` 库解析dump文件
3. **类型检测**：自动检测Wiki类型（Wikipedia/MediaWiki/Wikidata）
4. **提取数据**：
   - 页面标题、内容、URL
   - 内部链接关系
5. **导入数据库**：
   - 使用 `CSVImporter` 批量导入页面
   - 检查数据库，跳过已存在的URL
   - 使用 `import_edges` 导入链接关系

### 自动功能

- ✅ **自动检测Wiki类型**：根据dump文件中的站点信息
- ✅ **自动生成URL**：根据Wiki类型使用正确的URL格式
- ✅ **自动清理wikicode**：提取纯文本内容
- ✅ **自动跳过特殊页面**：跳过File、Image、Category等
- ✅ **自动去重**：跳过数据库中已存在的URL

## ⚙️ 配置要求

### 环境变量

确保 `.env` 文件中配置了：

```bash
CRAWL_PASSWORD=your-password-here
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-api-key
```

### Python依赖

确保安装了必需的库：

```bash
pip install mwxml mwparserfromhell
```

或在 `requirements.txt` 中已包含。

## 🐛 故障排除

### 问题 1: 上传失败 "密码错误"

**原因**：密码不正确或未配置

**解决**：
1. 检查 `.env` 文件中的 `CRAWL_PASSWORD`
2. 确保输入的密码正确
3. 重启服务器使配置生效

### 问题 2: 文件格式不支持

**原因**：文件不是XML格式的dump文件

**解决**：
- 确保文件扩展名是 `.xml`、`.xml.bz2` 或 `.xml.gz`
- 确保是MediaWiki/Wikipedia格式的XML dump

### 问题 3: 处理时间过长

**原因**：大型dump文件需要较长时间

**解决**：
- 使用"最大页面数"参数先测试小批量
- 查看服务器日志了解详细进度
- 处理完成后会自动清理临时文件

### 问题 4: 内存不足

**原因**：dump文件过大

**解决**：
- 限制处理页面数（使用max_pages参数）
- 分批处理dump文件
- 增加服务器内存

## 📊 API接口

### 上传接口

**POST** `/api/upload/xml-dump`

**参数**：
- `file` (File): XML Dump文件
- `password` (string): 密码
- `base_url` (string, 可选): Wiki基础URL
- `max_pages` (int, 可选): 最大处理页面数

**响应**：
```json
{
  "status": "processing",
  "message": "XML Dump文件已接收，开始解析和导入..."
}
```

## 🎉 优势

相比传统爬虫方式：

1. **更高效**：直接解析dump文件，无需HTTP请求
2. **更完整**：获取所有页面和链接关系
3. **更快速**：批量处理，无需等待网络延迟
4. **更可靠**：不触发反爬虫机制
5. **更灵活**：支持测试模式（限制页面数）

## 📚 相关文档

- `XML_DUMP_PROCESSOR_GUIDE.md` - XML Dump处理工具详细文档
- `MULTI_WIKI_SUPPORT.md` - 多Wiki类型支持说明
- `DATABASE_CACHE_OPTIMIZATION.md` - 数据库缓存优化
