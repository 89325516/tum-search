# 🚀 快速启动指南

## 当前状态

✅ **静态前端预览服务器已启动**
- 访问地址: http://localhost:8080/index.html
- 状态: 正在运行
- 功能: 可以查看前端界面（但API功能不可用）

## 完整启动后端服务器

### 步骤 1: 安装依赖

```bash
cd /Users/papersiii/tum-search
pip install -r requirements.txt
```

**注意**: 安装可能需要一些时间，特别是 torch 和 transformers 等大型库。

### 步骤 2: 配置环境变量

创建 `.env` 文件：

```bash
# 在项目根目录创建 .env 文件
cat > .env << EOF
QDRANT_URL=https://your-qdrant-instance.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
GOOGLE_API_KEY=your-google-gemini-api-key
EOF
```

**必需的配置**:
- `QDRANT_URL`: Qdrant 向量数据库的 URL
- `QDRANT_API_KEY`: Qdrant API 密钥

**可选的配置**:
- `GOOGLE_API_KEY`: Google Gemini API 密钥（用于内容摘要功能）

### 步骤 3: 启动后端服务器

#### 用户模式（推荐）
```bash
python3 web_server.py --mode user --port 8000
```

访问前端: **http://localhost:8000/static/index.html**

#### 管理员模式
```bash
python3 web_server.py --mode admin --port 8000
```

访问管理员界面: **http://localhost:8000/**

### 步骤 4: 验证服务器运行

启动后，你应该看到：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 📊 端口说明

- **8080**: 静态文件预览（当前运行中）
- **8000**: 后端服务器端口（需启动）
- **3000**: Vite 开发服务器端口（前端开发用）

## 🔍 检查依赖和配置

运行检查脚本：
```bash
python3 check_and_start.py
```

## ⚠️ 常见问题

### 1. 模块未找到错误
**解决方案**: 安装依赖
```bash
pip install -r requirements.txt
```

### 2. Qdrant 连接失败
**解决方案**: 检查 `.env` 文件中的 `QDRANT_URL` 和 `QDRANT_API_KEY` 是否正确

### 3. Google API 密钥未设置
**影响**: 内容摘要功能将不可用，但其他功能正常

### 4. 端口被占用
**解决方案**: 使用其他端口
```bash
python3 web_server.py --mode user --port 8001
```

## 🎯 当前可用功能

### 仅静态预览（端口 8080）
- ✅ 查看前端界面
- ✅ 查看页面布局和样式
- ❌ API 调用（需要后端服务器）

### 完整功能（端口 8000）
- ✅ 搜索功能
- ✅ 知识注入（URL/文本/图片上传）
- ✅ 实时通知（WebSocket）
- ✅ 热门内容展示
- ✅ 知识流展示

## 📝 下一步

1. **如果只想预览前端界面**: 
   - 继续使用 http://localhost:8080/index.html
   
2. **如果需要完整功能**:
   - 安装依赖: `pip install -r requirements.txt`
   - 配置 `.env` 文件
   - 启动后端服务器: `python3 web_server.py --mode user --port 8000`
   - 访问: http://localhost:8000/static/index.html
