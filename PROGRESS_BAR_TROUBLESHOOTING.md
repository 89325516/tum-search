# 进度条卡住问题 - 故障排除指南

## 问题描述
进度条一直卡在 "Waiting for crawler to start..." 状态

## 已完成的修复

### 1. WebSocket连接机制
- ✅ 添加了连接等待机制（最多等待3秒）
- ✅ 改进了broadcast函数的日志和错误处理
- ✅ 添加了连接状态检查

### 2. 消息发送机制
- ✅ 替换所有 `asyncio.run` 调用为 `broadcast_sync`
- ✅ 在爬虫开始前发送多次初始消息（确保到达）
- ✅ 添加了详细的调试日志

### 3. 爬虫错误处理
- ✅ 添加了爬虫启动错误捕获
- ✅ 添加了爬虫执行过程中的错误处理
- ✅ 所有错误都会通过WebSocket发送到前端

## 诊断步骤

### 步骤1：检查后端日志

当URL上传后，查看后端日志，应该能看到以下信息：

```
⏳ [AsyncTask] Starting task: url
⏳ [URL Task] Waiting for WebSocket connection... (0.1s)
✅ [URL Task] WebSocket connection(s) ready: 1
📢 [URL Task] About to send initial progress message...
✅ [Broadcast] Message sent to 1/1 connections: progress
✅ [URL Task] Initial progress message sent
🚀 [URL Task] Starting crawl for: <your-url>
🕸️ Starting recursive crawl: <your-url> (Depth: 8, Max Pages: 1000)
   📢 Initial callback sent
   🔍 Crawling: <your-url>
```

**如果看不到这些日志：**
- 后台任务可能没有启动
- 检查FastAPI是否正常运行

**如果看到 "⚠️ [Broadcast] No active WebSocket connections"：**
- WebSocket连接没有建立
- 检查浏览器控制台是否有WebSocket错误

### 步骤2：检查浏览器控制台

打开浏览器开发者工具（F12），查看Console标签：

应该看到：
```
✅ WebSocket connected successfully
WebSocket message received: {type: "progress", task_type: "url", ...}
```

**如果没有看到 "WebSocket connected"：**
- WebSocket连接失败
- 检查服务器是否运行在正确的端口
- 检查防火墙设置

**如果看到连接但收不到消息：**
- 消息可能没有发送
- 检查后端日志中的广播消息

### 步骤3：检查爬虫是否真正启动

在系统管理器中，爬虫启动会打印：
```
🕸️ Starting recursive crawl: <url>
```

如果看到这个消息但之后没有进度更新：
- 爬虫可能在第一个URL就卡住了
- 检查网络连接
- 检查目标URL是否可访问

### 步骤4：检查数据库

如果启用了 `check_db_first=True`：
- URL可能已经存在于数据库中
- 爬虫会跳过已存在的URL
- 如果所有URL都已存在，进度可能不会更新

## 常见问题

### Q1: 为什么进度条一直显示 "Waiting for crawler to start..."？
**A:** 可能的原因：
1. WebSocket消息没有发送成功
2. 前端没有正确处理消息
3. 爬虫没有真正启动

**解决方法：**
- 检查后端日志中的广播消息
- 检查浏览器控制台是否收到WebSocket消息
- 检查爬虫是否打印了启动日志

### Q2: 看到 "No active WebSocket connections" 警告
**A:** WebSocket连接没有建立

**解决方法：**
- 刷新页面，确保WebSocket连接建立
- 检查 `static/index.html` 中的WebSocket初始化代码
- 检查服务器是否正常运行

### Q3: 爬虫启动但没有进度更新
**A:** 可能的原因：
1. URL已经在数据库中，被跳过了
2. 爬虫卡在某个URL上
3. 回调函数没有被调用

**解决方法：**
- 查看后端日志，确认是否有 "Crawling:" 消息
- 查看是否有 "Progress updated:" 消息
- 检查URL是否可访问

## 调试技巧

1. **启用详细日志**
   - 所有关键步骤都有日志输出
   - 查看后端控制台的完整输出

2. **检查WebSocket连接**
   - 在浏览器Network标签中查看WebSocket连接状态
   - 查看是否有错误或断开连接

3. **测试单个URL**
   - 先测试一个简单的、已知可访问的URL
   - 确认爬虫基本功能正常

4. **检查网络环境**
   - 确保服务器可以访问目标URL
   - 检查是否有防火墙或代理问题

## 下一步

如果问题仍然存在，请提供：
1. 后端日志的完整输出（从URL上传开始）
2. 浏览器控制台的完整输出
3. 目标URL
4. 服务器环境信息

这些信息将帮助我们进一步诊断问题。
