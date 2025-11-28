# 启动服务器指南

## 🚀 启动后端服务器

### 前置条件

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**（创建 `.env` 文件）
   ```bash
   QDRANT_URL=https://your-qdrant-instance.qdrant.io
   QDRANT_API_KEY=your-api-key
   GOOGLE_API_KEY=your-google-api-key
   ```

### 启动方式

#### 方式1: 用户模式（默认端口 8000）
```bash
python3 web_server.py --mode user --port 8000
```

访问前端: http://localhost:8000/static/index.html

#### 方式2: 管理员模式
```bash
python3 web_server.py --mode admin --port 8000
```

访问管理员界面: http://localhost:8000/

#### 方式3: 使用 uvicorn 直接启动
```bash
uvicorn web_server:app --host 0.0.0.0 --port 8000
```

### API 端点

后端服务器提供以下 API：

- `GET /static/index.html` - 前端页面
- `GET /api/search?q=...` - 搜索API
- `GET /api/feed?limit=...` - 知识流
- `GET /api/trending?limit=...` - 热门内容
- `GET /api/item/{item_id}` - 内容详情
- `POST /api/upload/url` - URL上传
- `POST /api/upload/text` - 文本上传
- `POST /api/upload/image` - 图片上传
- `POST /api/feedback` - 用户反馈
- `WebSocket /ws` - 实时通知

### 端口说明

- **8000**: 默认后端服务器端口
- **8080**: 当前用于静态文件预览的端口
- **3000**: Vite 开发服务器端口（前端开发用）
- **7860**: Hugging Face Spaces 部署端口

### 注意事项

⚠️ 如果缺少环境变量，某些功能可能无法正常工作：
- 搜索功能需要 Qdrant 数据库
- 内容摘要需要 Google Gemini API
- 某些功能可能显示错误但不会崩溃

### 简化启动（仅预览前端）

如果只想预览前端界面，可以继续使用简单的 HTTP 服务器：
```bash
cd static
python3 -m http.server 8080
```

访问: http://localhost:8080/index.html
