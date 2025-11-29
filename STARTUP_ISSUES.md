# 服务器启动问题说明

## ⚠️ 当前问题

服务器已启动，但遇到 Qdrant 数据库连接问题。

### 错误信息

```
qdrant_client.http.exceptions.ResponseHandlingException: 
[Errno 8] nodename nor servname provided, or not known
```

这表明 `.env` 文件中的 `QDRANT_URL` 仍然是模板值，需要填入真实的 Qdrant 数据库 URL。

## 🔧 解决方案

### 步骤 1: 配置真实的 Qdrant 连接信息

编辑 `.env` 文件：

```bash
nano .env
# 或使用其他编辑器
```

将以下值替换为真实的配置：

```bash
# 必需：替换为你的真实 Qdrant 数据库 URL
QDRANT_URL=https://your-actual-cluster.qdrant.io

# 必需：替换为你的真实 API 密钥
QDRANT_API_KEY=your-actual-api-key-here

# 可选：Google Gemini API 密钥
GOOGLE_API_KEY=your-google-api-key-here
```

### 步骤 2: 获取 Qdrant 配置

如果你还没有 Qdrant 数据库：

1. **注册 Qdrant Cloud**:
   - 访问: https://cloud.qdrant.io/
   - 注册账号并创建集群

2. **获取连接信息**:
   - 在 Qdrant Cloud 控制台找到你的集群
   - 复制集群 URL 和 API Key

3. **或者使用本地 Qdrant**:
   ```bash
   # 使用 Docker 运行本地 Qdrant
   docker run -p 6333:6333 qdrant/qdrant
   ```
   然后设置：
   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=
   ```

### 步骤 3: 重启服务器

配置完成后，重启服务器：

```bash
# 停止当前服务器
kill $(cat server.pid)

# 重新启动
nohup python3 web_server.py --mode user --port 8000 > server.log 2>&1 &
echo $! > server.pid
```

## 📋 配置检查清单

- [ ] `.env` 文件中的 `QDRANT_URL` 是真实的数据库 URL
- [ ] `.env` 文件中的 `QDRANT_API_KEY` 是有效的 API 密钥
- [ ] 网络可以访问 Qdrant 数据库 URL
- [ ] 重启了服务器以加载新配置

## 🌐 临时解决方案

如果暂时无法配置 Qdrant，你可以：

1. **使用静态预览**（无 API 功能）:
   - 访问: http://localhost:8080/index.html
   - 已经运行中，可以预览前端界面

2. **使用模拟数据模式**（如果项目支持）:
   - 需要修改代码以支持离线模式

## 📝 相关文档

- `ENV_SETUP_GUIDE.md` - 详细的环境变量配置指南
- `QUICK_START.md` - 快速启动指南
- `SERVER_STATUS.md` - 服务器状态说明
