# 服务器启动状态

## 🚀 服务器启动信息

后端服务器正在启动中...

### 访问地址

- **前端界面**: http://localhost:8000/static/index.html
- **API 文档**: http://localhost:8000/docs
- **管理员界面**: http://localhost:8000/ (需要 --mode admin)

### 启动说明

服务器首次启动需要一些时间来完成：
1. ✅ 连接 Qdrant 数据库
2. ⏳ 加载 CLIP 模型（深度学习模型，约500MB）
3. ⏳ 初始化系统管理器
4. ⏳ 启动 FastAPI 服务器

**预计时间**: 1-3 分钟（取决于网络和系统性能）

### 检查服务器状态

```bash
# 检查进程
lsof -ti:8000

# 查看日志
tail -f server.log

# 测试服务器
curl http://localhost:8000/docs
```

### 停止服务器

```bash
# 如果使用 nohup 启动
kill $(cat server.pid)

# 或者查找进程
lsof -ti:8000 | xargs kill
```

### 常见问题

1. **端口被占用**
   ```bash
   # 使用其他端口
   python3 web_server.py --mode user --port 8001
   ```

2. **Qdrant 连接失败**
   - 检查 `.env` 文件中的 `QDRANT_URL` 和 `QDRANT_API_KEY`
   - 确保网络连接正常

3. **模型加载失败**
   - 首次运行需要下载模型（约500MB）
   - 确保有足够的磁盘空间和网络带宽

### 静态预览服务器

如果你只想预览前端界面（无 API 功能），可以使用：

- **静态预览**: http://localhost:8080/index.html （已在运行）
