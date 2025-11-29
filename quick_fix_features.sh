#!/bin/bash
# 快速修复功能脚本 - 重启服务器并清除缓存提示

echo "🔧 功能修复脚本"
echo "================"
echo ""

# 1. 检查服务器进程
echo "1️⃣ 检查服务器进程..."
SERVER_PID=$(ps aux | grep "web_server.py\|uvicorn" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$SERVER_PID" ]; then
    echo "   ⚠️  发现运行中的服务器进程 (PID: $SERVER_PID)"
    echo "   🔄 停止旧服务器..."
    pkill -f "web_server.py"
    pkill -f "uvicorn"
    sleep 2
    echo "   ✅ 服务器已停止"
else
    echo "   ✅ 没有运行中的服务器"
fi

# 2. 检查代码
echo ""
echo "2️⃣ 检查功能代码..."
if [ -f "static/index.html" ]; then
    HAS_GRAPH=$(grep -c "tab-graph" static/index.html)
    HAS_HIGHLIGHT=$(grep -c "highlighted_snippet" static/index.html)
    echo "   - Graph View: $HAS_GRAPH 处代码"
    echo "   - 摘要高亮: $HAS_HIGHLIGHT 处代码"
else
    echo "   ❌ static/index.html 不存在！"
    exit 1
fi

# 3. 启动服务器
echo ""
echo "3️⃣ 启动服务器..."
echo "   📍 服务器将运行在: http://localhost:8000"
echo "   ⏳ 启动中..."
echo ""

# 后台启动服务器
nohup python3 web_server.py --mode user --port 8000 > server.log 2>&1 &
SERVER_NEW_PID=$!

sleep 3

# 检查是否启动成功
if ps -p $SERVER_NEW_PID > /dev/null; then
    echo "   ✅ 服务器已启动 (PID: $SERVER_NEW_PID)"
else
    echo "   ❌ 服务器启动失败，查看 server.log 了解详情"
    exit 1
fi

# 4. 提示用户
echo ""
echo "✅ 修复完成！"
echo "================"
echo ""
echo "📋 下一步操作："
echo "   1. 打开浏览器"
echo "   2. 访问: http://localhost:8000/"
echo "   3. 硬刷新页面 (Ctrl+Shift+R 或 Cmd+Shift+R)"
echo "   4. 搜索关键词（如 'TUM'）"
echo "   5. 查看是否有 Graph View Tab 和摘要高亮"
echo ""
echo "📊 查看服务器日志:"
echo "   tail -f server.log"
echo ""
echo "🛑 停止服务器:"
echo "   kill $SERVER_NEW_PID"
echo ""
