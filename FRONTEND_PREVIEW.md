# 前端页面预览说明

## 🎨 前端界面概览

TUM Search Engine 前端是一个现代化的 React 应用，具有以下主要功能和界面：

### 📋 主要界面组件

#### 1. **顶部导航栏 (Navbar)**
- **Logo**: TUM Neural Net (渐变文字效果)
- **导航链接**: Home, Knowledge Graph, About
- **系统状态指示器**: 显示 "System Active" (绿色脉冲动画)

#### 2. **3D 粒子网络背景**
- 动态粒子网络动画
- 鼠标交互效果（鼠标附近的粒子会被吸引）
- 蓝色渐变粒子效果
- 连接线动态绘制

#### 3. **主搜索区域**
- **大标题**: "TUM Neural Knowledge Network"
- **搜索框**: 
  - 大尺寸搜索输入框
  - 搜索图标
  - 渐变边框效果
  - 占位符文本提示
- **搜索按钮**: 渐变背景，悬停效果
- **副标题**: "Discover knowledge through semantic convergence"

#### 4. **搜索算法步骤可视化**
搜索时会显示算法执行步骤：
- Step 1: Query Vectorization (查询向量化)
- Step 2: Similarity Search (相似度搜索)
- Step 3: Ranking & Filtering (排序和过滤)
- Step 4: Result Convergence (结果聚合)

每个步骤都有进度指示和状态显示

#### 5. **搜索结果卡片**
- 玻璃态效果卡片 (Glass morphism)
- 显示内容类型、URL、预览文本
- 相关性分数显示
- 点击跳转到详情页
- 悬停高亮效果

#### 6. **热门内容区域 (Trending)**
- 显示热门/趋势内容
- 卡片网格布局
- 类型标签（如 "Page", "Article" 等）
- 内容预览和元数据

#### 7. **知识流区域 (Feed)**
- 实时知识流展示
- 3列网格布局（响应式）
- 深色半透明卡片
- 内容类型、URL、预览
- ID 显示

#### 8. **知识注入面板 (Knowledge Injection)**
- **标签页切换**:
  - 📝 Text Upload (文本上传)
  - 🔗 URL Upload (URL上传)
  - 🖼️ Image Upload (图片上传)
- **URL上传**: 输入框 + 提交按钮
- **文本上传**: 多行文本输入 + 提交
- **图片上传**: 文件选择器 + 预览

#### 9. **通知系统**
- **进度提示**: 右下角进度通知
  - 显示处理项目数量
  - 进度条动画
  - 详细信息显示
- **系统更新通知**: WebSocket 实时通知
- **错误提示**: 红色错误提示

#### 10. **教育卡片 (How it Works)**
- 解释系统工作原理
- 图标 + 描述布局
- 平滑滚动效果

### 🎨 设计特点

1. **玻璃态设计 (Glassmorphism)**
   - 半透明背景
   - 模糊效果 (backdrop-filter)
   - 边框高光

2. **渐变效果**
   - Logo 渐变文字
   - 按钮渐变背景
   - 底部装饰渐变条

3. **深色主题**
   - 深色背景 (#0f172a)
   - 蓝色/青色强调色
   - 半透明卡片

4. **响应式设计**
   - 移动端适配
   - 灵活的网格布局
   - 自适应字体大小

5. **动画效果**
   - 粒子网络动画
   - 悬停过渡效果
   - 进度条动画
   - 状态指示器脉冲

### 🔧 技术栈

- **React 18** - UI框架
- **Vite** - 构建工具和开发服务器
- **Tailwind CSS** - 样式框架（CDN）
- **Lucide React** - 图标库
- **WebSocket** - 实时通信

### 📱 页面结构

```
┌─────────────────────────────────────┐
│  Navigation Bar                     │
│  (Logo + Links + Status)            │
├─────────────────────────────────────┤
│                                     │
│  [3D Particle Background]           │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  TUM Neural Knowledge Net   │   │
│  │  [Search Box] [Search Btn]  │   │
│  └─────────────────────────────┘   │
│                                     │
│  [Search Steps Visualization]       │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Search Results Grid        │   │
│  │  [Card] [Card] [Card] ...   │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Trending Section           │   │
│  │  [Hot Content Cards]        │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Knowledge Feed             │   │
│  │  [Feed Items Grid]          │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Knowledge Injection Panel  │   │
│  │  [Upload Tabs]              │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

### 🚀 预览方式

#### 方式1: 使用 Vite 开发服务器（推荐）

```bash
cd frontend
npm install
npm run dev
```

然后在浏览器访问: `http://localhost:3000`

#### 方式2: 通过后端服务器（已构建的静态版本）

```bash
# 启动后端服务器
python3 web_server.py --mode user --port 8000
```

然后在浏览器访问: `http://localhost:8000/static/index.html`

#### 方式3: 直接打开 HTML 文件（静态版本）

在 `static/` 目录下有已经构建好的 HTML 版本：
- `static/index.html` - 用户搜索界面
- `static/admin.html` - 管理员控制台
- `static/view.html` - 内容详情页

### 📸 界面截图描述

1. **主页面**:
   - 深色背景上的3D粒子网络
   - 中心位置的搜索框
   - 渐变色的Logo和标题
   - 底部显示热门内容和知识流

2. **搜索中**:
   - 算法步骤可视化面板
   - 进度指示器
   - 动态步骤高亮

3. **搜索结果**:
   - 网格布局的结果卡片
   - 每个卡片显示类型、URL、预览
   - 相关性分数徽章

4. **知识注入**:
   - 展开的面板
   - 三个标签页切换
   - 上传表单界面

### 🎯 主要功能

1. ✅ **语义搜索**: 基于向量空间的智能搜索
2. ✅ **实时更新**: WebSocket 实时通知
3. ✅ **知识注入**: URL/文本/图片上传
4. ✅ **热门内容**: 展示趋势内容
5. ✅ **知识流**: 实时知识流展示
6. ✅ **用户交互**: 点击追踪和反馈
7. ✅ **响应式**: 移动端适配

### 📝 注意事项

- 前端需要后端 API 支持才能完整工作
- WebSocket 连接需要后端 WebSocket 服务
- 如果前后端分离部署，需要配置 CORS
- API 端点配置在 `config.js` 中

### 🔗 相关文件

- `frontend/App.jsx` - React 主组件（907行）
- `frontend/main.jsx` - React 入口
- `frontend/index.html` - HTML 模板
- `frontend/config.js` - API 配置
- `static/index.html` - 静态 HTML 版本
- `web_server.py` - 后端服务器（提供静态文件服务）
