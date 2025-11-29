#!/bin/bash
# 推送到 GitHub 的脚本
# 使用方法：在终端运行此脚本，然后输入您的 GitHub 用户名和 Personal Access Token

cd /Users/papersiii/.cursor/worktrees/tum-search/akw

echo "=========================================="
echo "准备推送到 GitHub"
echo "=========================================="
echo ""
echo "当前工作目录: $(pwd)"
echo ""
echo "将要推送以下提交到 origin/main:"
git log --oneline origin/main..main
echo ""
echo "=========================================="
echo "开始推送..."
echo "=========================================="
echo ""
echo "提示：当系统要求输入时"
echo "  - Username: 输入您的 GitHub 用户名"
echo "  - Password: 粘贴您的 Personal Access Token（不是密码！）"
echo ""

# 使用 --force-with-lease 安全推送
git push origin main --force-with-lease

# 检查推送结果
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 推送成功！"
    echo "=========================================="
    echo ""
    echo "您可以在 GitHub 上查看推送的提交："
    echo "https://github.com/89325516/tum-search/commits/main"
else
    echo ""
    echo "=========================================="
    echo "❌ 推送失败"
    echo "=========================================="
    echo ""
    echo "请检查："
    echo "1. 网络连接是否正常"
    echo "2. GitHub 用户名是否正确"
    echo "3. Personal Access Token 是否有效且有推送权限"
    exit 1
fi

