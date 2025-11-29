# Qdrant 数据库配置指南

## 📋 配置选项

有两种方式可以配置 Qdrant 数据库：

### 选项 1: 使用 Qdrant Cloud（推荐，简单快速）

适合快速开始，无需本地安装。

#### 步骤：

1. **注册 Qdrant Cloud**
   - 访问: https://cloud.qdrant.io/
   - 使用邮箱或 GitHub 账号注册

2. **创建集群**
   - 登录后点击 "Create Cluster"
   - 选择免费套餐（Free tier）
   - 选择地区（推荐选择离你最近的）
   - 等待集群创建完成（通常 1-2 分钟）

3. **获取连接信息**
   - 进入集群详情页面
   - 复制 **Cluster URL**（例如：`https://xxxxx-xxxxx-xxxxx.qdrant.io`）
   - 进入 "API Keys" 标签页
   - 创建新的 API Key 并复制

4. **配置 .env 文件**
   ```bash
   QDRANT_URL=https://你的集群ID.qdrant.io
   QDRANT_API_KEY=你的API密钥
   ```

### 选项 2: 使用本地 Docker（适合开发和测试）

适合想要完全控制或离线使用的情况。

#### 步骤：

1. **启动本地 Qdrant**
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 \
     -v $(pwd)/qdrant_storage:/qdrant/storage \
     qdrant/qdrant
   ```

2. **配置 .env 文件**
   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=
   ```
   
   > 注意：本地 Docker 版本不需要 API Key，可以留空

3. **验证本地 Qdrant 运行**
   ```bash
   curl http://localhost:6333/collections
   ```

## 🔧 配置 .env 文件

编辑 `.env` 文件，将模板值替换为真实的配置：

```bash
# 使用你喜欢的编辑器
nano .env
# 或
vim .env
# 或使用 VS Code
code .env
```

### Qdrant Cloud 配置示例：

```bash
QDRANT_URL=https://abc123-xyz456-789.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 本地 Docker 配置示例：

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

## ✅ 验证配置

配置完成后，运行检查脚本：

```bash
python3 check_and_start.py
```

或者手动测试连接：

```bash
python3 -c "
from dotenv import load_dotenv
import os
from qdrant_client import QdrantClient

load_dotenv()
url = os.getenv('QDRANT_URL')
key = os.getenv('QDRANT_API_KEY')

try:
    client = QdrantClient(url=url, api_key=key if key else None)
    collections = client.get_collections()
    print('✅ Qdrant 连接成功！')
    print(f'   当前集合数: {len(collections.collections)}')
except Exception as e:
    print(f'❌ 连接失败: {e}')
"
```

## 🚀 配置完成后

1. **重启服务器**：
   ```bash
   kill $(cat server.pid) 2>/dev/null
   nohup python3 web_server.py --mode user --port 8000 > server.log 2>&1 &
   echo $! > server.pid
   ```

2. **查看启动日志**：
   ```bash
   tail -f server.log
   ```

3. **访问前端**：
   - http://localhost:8000/static/index.html

## 💡 推荐选择

- **首次使用或快速开始**: 选择 **Qdrant Cloud**（选项1）
- **开发测试或需要完全控制**: 选择 **本地 Docker**（选项2）

## 📝 注意事项

1. **Qdrant Cloud 免费套餐限制**:
   - 1GB 存储
   - 适合开发和测试

2. **本地 Docker**:
   - 需要安装 Docker
   - 数据存储在本地
   - 不需要网络连接（启动后）

3. **安全性**:
   - 不要将 `.env` 文件提交到 Git
   - 保护你的 API 密钥
