#!/bin/bash
# 依赖库安装脚本

echo "🚀 开始安装依赖库..."
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📌 Python版本: $python_version"

# 升级pip
echo ""
echo "📦 升级pip..."
pip3 install --upgrade pip

# 安装依赖
echo ""
echo "📦 安装依赖库（从requirements.txt）..."
pip3 install -r requirements.txt

# 检查关键依赖
echo ""
echo "🔍 检查关键依赖..."
python3 check_dependencies.py

echo ""
echo "✅ 安装完成！"
echo ""
echo "如果还有缺失的依赖，请运行："
echo "  pip3 install mwxml mwparserfromhell"
