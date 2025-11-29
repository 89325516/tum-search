# 环境变量配置指南

## 📝 .env 文件配置

`.env` 文件已创建，现在需要填入真实的配置值。

### 必需的配置

#### 1. Qdrant 向量数据库配置

**QDRANT_URL**
- 描述: Qdrant 向量数据库的 URL
- 示例值:
  - 云端: `https://xxxxx-xxxxx-xxxxx.qdrant.io`
  - 本地: `http://localhost:6333`
- 如何获取:
  1. 注册 Qdrant Cloud: https://cloud.qdrant.io/
  2. 创建集群后，在控制台查看 URL

**QDRANT_API_KEY**
- 描述: Qdrant API 密钥
- 示例值: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- 如何获取:
  1. 在 Qdrant Cloud 控制台中
  2. 进入集群设置 → API Keys
  3. 创建新的 API Key

### 可选的配置

#### 2. Google Gemini API 配置

**GOOGLE_API_KEY**
- 描述: Google Gemini API 密钥，用于内容摘要功能
- 默认: 如果未设置，摘要功能将不可用，但其他功能正常
- 如何获取:
  1. 访问: https://makersuite.google.com/app/apikey
  2. 登录 Google 账号
  3. 创建新的 API Key
  4. 复制密钥到 `.env` 文件

### 配置示例

编辑 `.env` 文件，填入你的配置：

```bash
# Qdrant 配置（必需）
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your-actual-api-key-here

# Google Gemini 配置（可选）
GOOGLE_API_KEY=your-google-api-key-here
```

### 验证配置

运行检查脚本验证配置：

```bash
python3 check_and_start.py
```

### 配置说明

1. **不要提交 .env 文件到 Git**
   - `.env` 文件已添加到 `.gitignore`
   - 只提交 `.env.example` 作为模板

2. **配置完成后重启服务器**
   - 环境变量在服务器启动时加载
   - 修改后需要重启才能生效

3. **安全性**
   - 不要分享你的 API 密钥
   - 定期轮换 API 密钥
   - 使用最小权限原则

## 🔧 快速配置命令

如果你已经有配置值，可以直接编辑 `.env` 文件：

```bash
# 使用 nano 编辑器
nano .env

# 或使用 vim
vim .env

# 或使用 VS Code
code .env
```

填入你的真实配置值后保存即可。

## ✅ 配置检查清单

- [ ] QDRANT_URL 已设置为真实的 Qdrant 集群 URL
- [ ] QDRANT_API_KEY 已设置为有效的 API 密钥
- [ ] GOOGLE_API_KEY 已设置（可选，用于摘要功能）
- [ ] 运行 `python3 check_and_start.py` 验证配置

## 🚀 下一步

配置完成后，启动服务器：

```bash
python3 web_server.py --mode user --port 8000
```

然后访问: http://localhost:8000/static/index.html
