# 快速配置指南

## 🚀 快速开始（3 步完成配置）

### 步骤 1: 获取 Qdrant Cloud 账号

1. 访问 https://cloud.qdrant.io/
2. 使用邮箱或 GitHub 注册账号
3. 创建集群（选择免费套餐）
4. 等待集群创建完成（1-2分钟）

### 步骤 2: 获取连接信息

在集群详情页面找到：

**Cluster URL** (例如):
```
https://abc123-xyz456-789.qdrant.io
```

**API Key**:
1. 点击 "API Keys" 标签页
2. 点击 "Create API Key"
3. 复制生成的 API Key（以 `eyJ...` 开头）

### 步骤 3: 配置 .env 文件

运行配置助手：

```bash
python3 configure_qdrant.py
```

或者手动编辑 `.env` 文件：

```bash
QDRANT_URL=https://你的集群URL.qdrant.io
QDRANT_API_KEY=你的API密钥
```

## ✅ 验证配置

配置完成后，测试连接：

```bash
python3 check_and_start.py
```

或者使用配置助手的测试功能。

## 🔄 重启服务器

```bash
# 停止当前服务器
kill $(cat server.pid) 2>/dev/null

# 重新启动
nohup python3 web_server.py --mode user --port 8000 > server.log 2>&1 &
echo $! > server.pid

# 查看日志
tail -f server.log
```

## 📝 配置示例

### Qdrant Cloud 配置

```bash
QDRANT_URL=https://abc123-xyz456-789.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...
```

### 本地 Docker 配置（如果安装了 Docker）

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

## ⚠️ 注意事项

1. 不要将 `.env` 文件提交到 Git
2. 保护你的 API 密钥，不要分享
3. Qdrant Cloud 免费套餐有 1GB 存储限制

## 📖 更多信息

- `QDRANT_SETUP.md` - 详细配置说明
- `ENV_SETUP_GUIDE.md` - 环境变量完整指南
