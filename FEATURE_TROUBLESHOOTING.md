# 功能故障排除指南

## 🔍 问题诊断

如果Graph View和摘要高亮功能无法使用，按照以下步骤排查：

## ✅ 步骤1：确认代码已更新

运行功能检查脚本：
```bash
cd /Users/papersiii/tum-search
python3 check_features.py
```

**应该看到**：✅ 所有功能代码检查通过

## 🚀 步骤2：重启服务器（最重要！）

### 检查服务器是否在运行

```bash
ps aux | grep "web_server.py\|uvicorn" | grep -v grep
```

### 停止旧服务器

```bash
# 方法1：查找并杀死进程
pkill -f "web_server.py"

# 方法2：如果知道端口，查找PID
lsof -ti:8000 | xargs kill -9
```

### 启动新服务器

```bash
cd /Users/papersiii/tum-search
python3 web_server.py --mode user --port 8000
```

**确认启动成功**：应该看到类似以下输出
```
🚀 Server starting in USER mode
```

## 🌐 步骤3：清除浏览器缓存

### 方法1：硬刷新
- **Windows/Linux**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`

### 方法2：使用无痕模式
在新无痕窗口中访问：`http://localhost:8000/`

### 方法3：清除所有缓存
1. 打开浏览器设置
2. 清除浏览数据
3. 选择"缓存的图片和文件"
4. 清除数据

## 🔎 步骤4：验证功能

### 测试Graph View

1. **访问页面**：`http://localhost:8000/`
2. **搜索关键词**：输入 "TUM" 并点击搜索
3. **查看搜索结果区域上方**：
   - ✅ 应该看到两个Tab按钮
   - ✅ "List View"（列表视图）
   - ✅ "Graph View"（网络图视图）
4. **点击 "Graph View" Tab**：
   - ✅ 应该显示网络图
   - ✅ 有节点和连线

### 测试摘要高亮

1. **搜索关键词**：输入 "TUM Computer Science"
2. **查看搜索结果**：
   - ✅ 关键词（如 "TUM", "Computer", "Science"）应该以**青色加粗**显示
   - ✅ 关键词有半透明青色背景

## 🐛 常见问题

### 问题1：看不到Graph View Tab

**症状**：搜索后只看到结果列表，没有Tab切换按钮

**可能原因**：
1. ❌ 浏览器缓存了旧页面
2. ❌ 服务器没有重启
3. ❌ 访问了错误的URL

**解决方案**：
```bash
# 1. 确认访问正确的URL
# ✅ http://localhost:8000/
# ✅ http://localhost:8000/static/index.html

# 2. 重启服务器
pkill -f "web_server.py"
python3 web_server.py --mode user --port 8000

# 3. 在浏览器中硬刷新（Ctrl+Shift+R）
```

### 问题2：摘要高亮不显示

**症状**：搜索结果中的关键词没有加粗或高亮

**检查方法**：
1. 打开浏览器开发者工具（F12）
2. 切换到 **Network** 标签
3. 执行搜索
4. 查看 `/api/search?q=...` 请求的响应
5. 检查 `results[0].highlighted_snippet` 是否存在

**解决方案**：
- 如果API响应中没有 `highlighted_snippet` 字段，检查后端代码
- 如果字段存在但前端不显示，检查浏览器控制台错误

### 问题3：Graph View为空或报错

**症状**：点击Graph View后显示空白或错误

**检查方法**：
打开浏览器控制台（F12），查看错误信息

**可能错误**：
- `echarts is not defined` → ECharts库未加载
- `Cannot read property 'init'` → 容器元素未找到

**解决方案**：
1. 检查网络连接（需要加载ECharts CDN）
2. 检查 `graph-container` 元素是否存在
3. 查看浏览器控制台的完整错误信息

## 🔧 手动测试API

### 测试搜索API（检查摘要高亮）

```bash
curl "http://localhost:8000/api/search?q=TUM" | python3 -m json.tool | grep -A 5 "highlighted_snippet" | head -10
```

**应该看到**：包含 `[[HIGHLIGHT]]` 标记的文本

### 测试Graph API

```bash
curl "http://localhost:8000/api/search/graph?q=TUM&max_nodes=10" | python3 -m json.tool | head -30
```

**应该看到**：包含 `nodes` 和 `edges` 数组的JSON

## 📋 完整检查清单

- [ ] 服务器已重启（ps aux | grep web_server）
- [ ] 访问正确的URL（http://localhost:8000/）
- [ ] 浏览器缓存已清除（Ctrl+Shift+R）
- [ ] 浏览器控制台无错误（F12 → Console）
- [ ] 搜索结果API返回了 `highlighted_snippet` 字段
- [ ] Graph API返回了 `nodes` 和 `edges` 数据
- [ ] Tab按钮出现在搜索结果上方
- [ ] 点击Graph View Tab后显示网络图
- [ ] 搜索结果中关键词被高亮显示

## 🆘 如果仍然无法使用

### 收集诊断信息

1. **服务器日志**：
   ```bash
   # 查看服务器终端输出
   # 检查是否有错误信息
   ```

2. **浏览器控制台**：
   - 按F12打开开发者工具
   - 切换到Console标签
   - 复制所有错误信息

3. **网络请求**：
   - F12 → Network标签
   - 执行搜索
   - 查看 `/api/search` 和 `/api/search/graph` 的响应

4. **页面源代码**：
   - 在浏览器中查看页面源代码
   - 搜索 "Graph View" 或 "tab-graph"
   - 确认代码是否在页面中

### 快速重置步骤

```bash
# 1. 停止所有服务器进程
pkill -f "web_server.py"
pkill -f "uvicorn"

# 2. 确认代码是最新的
cd /Users/papersiii/tum-search
git log --oneline -3

# 3. 重启服务器
python3 web_server.py --mode user --port 8000

# 4. 在新无痕窗口中访问
# http://localhost:8000/
```

## 📞 提供调试信息

如果问题仍未解决，请提供：

1. **代码检查结果**：
   ```bash
   python3 check_features.py
   ```

2. **浏览器控制台错误**（F12 → Console）

3. **API响应示例**：
   ```bash
   curl "http://localhost:8000/api/search?q=TUM" | head -50
   ```

4. **访问的URL**

5. **服务器日志输出**
