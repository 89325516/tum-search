# TUM Search Engine - 前端部分

这是 TUM Search Engine 的前端部分，已从后端项目中独立提取出来。

## 文件结构

```
frontend/
├── App.jsx         # React主组件（整合所有功能）
├── main.jsx        # React入口文件
├── index.html      # HTML入口（React版本）
├── admin.html      # 管理员控制台（Vue版本）
├── view.html       # 内容详情页面（原生HTML）
├── config.js       # API配置文件
└── README.md       # 本文件
```

## 版本说明

### React版本（推荐）
- **App.jsx** - 使用React构建的现代化前端，整合了所有功能
- **main.jsx** - React应用入口
- **index.html** - React版本的HTML入口

### 原生HTML版本（备用）
- **index.html** (原版本) - 原生HTML + JavaScript实现
- **admin.html** - Vue.js实现的管理员控制台
- **view.html** - 原生HTML实现的详情页面

## 功能说明

### App.jsx (React版本 - 推荐)
- ✅ 用户搜索界面（带算法步骤可视化）
- ✅ 知识注入功能（URL、文本上传）
- ✅ 实时系统更新通知（WebSocket）
- ✅ 热门内容展示（Trending）
- ✅ 知识流展示（Feed）
- ✅ 教育卡片（How it Works）
- ✅ 用户交互记录
- ✅ 3D粒子网络背景动画
- ✅ 响应式设计

### index.html (原生HTML版本)
- 用户搜索界面
- 知识注入功能（URL、文本上传）
- 实时系统更新通知（WebSocket）
- 热门内容展示
- 知识流展示

### admin.html
- 管理员控制台
- 浏览和管理 Space R 和 Space X
- 提升内容到 Space R
- 删除内容

### view.html
- 内容详情页面
- 语义相似推荐
- 协同过滤推荐（社区路径）

## 配置

### API端点配置

编辑 `config.js` 文件来配置后端API地址：

```javascript
const API_CONFIG = {
    baseURL: window.location.origin, // 默认使用当前域名
    // 如果前后端分离，设置为: 'https://api.example.com'
    ...
};
```

### 开发环境配置

如果前端和后端运行在不同的端口，需要修改 `config.js`：

```javascript
if (window.location.hostname === 'localhost') {
    API_CONFIG.baseURL = 'http://localhost:8000';  // 后端端口
    API_CONFIG.wsURL = 'ws://localhost:8000';
}
```

## 使用方法

### React版本（推荐）

#### 安装依赖

```bash
cd frontend
npm install react react-dom
# 或使用yarn
yarn add react react-dom
```

#### 使用Vite构建（推荐）

```bash
# 安装Vite
npm install -D vite @vitejs/plugin-react

# 创建vite.config.js
# 运行开发服务器
npm run dev
```

#### 使用Create React App

```bash
npx create-react-app .
# 将App.jsx和main.jsx复制到src目录
npm start
```

### 原生HTML版本

#### 方式1: 与后端一起部署（推荐）

如果前端和后端部署在同一服务器上，可以直接使用：

1. 将 `frontend/` 目录中的文件复制到后端的 `static/` 目录
2. 后端会自动提供静态文件服务

#### 方式2: 独立部署前端

如果前端需要独立部署（例如使用 Nginx、Vercel、Netlify 等）：

1. 修改 `config.js` 中的 `baseURL` 为后端API地址
2. 配置CORS，允许前端域名访问后端API
3. 部署前端文件到静态文件服务器

#### 方式3: 本地开发

使用简单的HTTP服务器：

```bash
# 使用Python
cd frontend
python3 -m http.server 3000

# 或使用Node.js的http-server
npx http-server -p 3000
```

然后在浏览器中访问 `http://localhost:3000`

**注意**: 需要确保后端API已启动，并且配置了正确的CORS策略。

## API依赖

前端依赖以下后端API端点：

- `GET /api/search?q=...` - 搜索
- `GET /api/feed?limit=...&offset=...` - 获取知识流
- `GET /api/trending?limit=...` - 获取热门内容
- `GET /api/item/{item_id}` - 获取内容详情
- `POST /api/feedback` - 记录用户交互
- `POST /api/upload/url` - 上传URL
- `POST /api/upload/text` - 上传文本
- `POST /api/upload/image` - 上传图片
- `WebSocket /ws` - 实时更新通知

管理员功能还需要：
- `GET /api/admin/browse?space=...&limit=...&offset=...`
- `POST /api/admin/promote`
- `DELETE /api/admin/delete?space=...&id=...`

## 技术栈

### React版本
- **React 18+** - UI框架
- **Tailwind CSS** - 样式框架（CDN）
- **Lucide React** - 图标库
- **WebSocket** - 实时通信

### 原生HTML版本
- **index.html & view.html**: Tailwind CSS (CDN)
- **admin.html**: Bootstrap 5 + Vue.js 3
- 纯JavaScript，无需构建工具

## 注意事项

1. 所有API调用都使用相对路径，通过 `config.js` 统一管理
2. WebSocket连接用于实时通知，需要后端支持
3. 前端使用CDN加载CSS框架，需要网络连接
4. 如果部署到生产环境，建议将CDN资源本地化以提高性能和稳定性

