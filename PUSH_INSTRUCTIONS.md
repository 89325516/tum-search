# 推送到 GitHub 的说明

## 📦 准备推送的提交

以下提交将推送到 GitHub：

1. `5d213a6` - Merge origin/main: Resolve conflict in crawler.py, keep improved headers with longer timeout
2. `b4327a9` - Update crawler fixes summary and crawler.py  
3. `edee364` - The front-end was beautified and the web crawler was rewritten and optimized.

## 🚀 推送方法

### 方法 1: 使用推送脚本（推荐）

```bash
cd /Users/papersiii/.cursor/worktrees/tum-search/akw
./push_to_github.sh
```

脚本会引导您输入 GitHub 用户名和 Personal Access Token。

### 方法 2: 直接运行 Git 命令

在终端运行以下命令：

```bash
cd /Users/papersiii/.cursor/worktrees/tum-search/akw
git push origin main --force-with-lease
```

**当提示输入时：**
- **Username**: 输入 `89325516` 或您的 GitHub 用户名
- **Password**: 粘贴您的 **Personal Access Token**（不是密码！）

### 方法 3: 在 URL 中包含 Token（一次性使用）

如果您想一次性推送而不每次都输入，可以临时修改远程 URL：

```bash
cd /Users/papersiii/.cursor/worktrees/tum-search/akw

# 替换 YOUR_TOKEN 为您的 Personal Access Token
git remote set-url origin https://YOUR_TOKEN@github.com/89325516/tum-search.git

# 推送
git push origin main --force-with-lease

# 推送完成后，恢复原始 URL（安全起见）
git remote set-url origin https://github.com/89325516/tum-search.git
```

## ✅ 验证推送结果

推送成功后，可以在以下地址查看：

https://github.com/89325516/tum-search/commits/main

## 🔒 安全提示

- Personal Access Token 是敏感信息，不要分享给他人
- 推送后建议恢复原始的远程 URL（如果使用方法 3）
- Token 会自动保存在 macOS 钥匙串中，之后推送无需重复输入

