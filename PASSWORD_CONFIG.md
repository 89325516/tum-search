# 爬取密码配置说明

## 🔐 密码说明

系统使用环境变量 `CRAWL_PASSWORD` 来配置爬取密码。这个密码用于保护以下功能：

- ✅ URL爬取功能
- ✅ CSV批量导入功能
- ✅ XML Dump上传功能

## 📋 当前状态

### 检查密码配置

运行以下命令检查密码是否已配置：

```bash
# 检查.env文件中是否配置了密码
grep CRAWL_PASSWORD .env
```

### 如果未配置

如果`.env`文件中没有`CRAWL_PASSWORD`配置，系统会：
- 显示错误："服务器未配置爬取密码，请联系管理员"
- 阻止所有需要密码的操作

## 🔧 如何设置密码

### 方法1: 在.env文件中配置（推荐）

1. **编辑.env文件**
   ```bash
   # 在项目根目录编辑.env文件
   nano .env
   # 或
   vim .env
   ```

2. **添加密码配置**
   ```bash
   CRAWL_PASSWORD=your-secure-password-here
   ```

3. **重启服务器**
   ```bash
   # 停止服务器
   pkill -f web_server.py
   
   # 重新启动
   python3 web_server.py --mode user --port 8000
   ```

### 方法2: 使用环境变量（临时）

```bash
# 设置环境变量
export CRAWL_PASSWORD=your-secure-password-here

# 启动服务器
python3 web_server.py --mode user --port 8000
```

### 方法3: 复制示例文件

```bash
# 如果.env文件不存在，从示例文件创建
cp .env.example .env

# 然后编辑.env文件，设置密码
nano .env
```

## 🔒 密码安全建议

1. **使用强密码**
   - 至少12个字符
   - 包含大小写字母、数字、特殊字符
   - 例如：`MySecure@Pass123!`

2. **不要分享密码**
   - 只在需要访问的用户之间分享
   - 不要在代码中硬编码密码

3. **定期更换**
   - 建议每3-6个月更换一次
   - 如果怀疑泄露，立即更换

4. **保护.env文件**
   - `.env`文件已在`.gitignore`中
   - 不要将`.env`文件提交到Git仓库
   - 确保文件权限正确（仅所有者可读）

## 🎯 使用密码

配置密码后，在前端界面使用以下功能时需要输入密码：

### 1. URL爬取
- 在"URL Injection"区域
- 输入URL和密码
- 点击"Inject"按钮

### 2. CSV批量导入
- 在"Batch Import (Wiki Style)"区域
- 选择CSV文件
- 输入URL前缀（可选）
- 输入密码
- 点击"批量导入"按钮

### 3. Wiki Dump上传
- 在"Wiki Dump Import"区域
- 选择XML dump文件
- 输入Wiki基础URL（可选）
- 输入最大页面数（可选）
- 输入密码
- 点击"导入Dump"按钮

## ❓ 常见问题

### Q1: 密码是什么？

**A**: 密码是您在`.env`文件中配置的`CRAWL_PASSWORD`值。如果您没有配置，系统会提示错误。

### Q2: 如何查看当前配置的密码？

**A**: 密码存储在`.env`文件中。您可以查看：
```bash
grep CRAWL_PASSWORD .env
```

**注意**：出于安全考虑，不要在公共场所显示密码。

### Q3: 忘记密码怎么办？

**A**: 
1. 编辑`.env`文件
2. 修改`CRAWL_PASSWORD`的值
3. 重启服务器

### Q4: 如何重置密码？

**A**: 修改`.env`文件中的`CRAWL_PASSWORD`值即可。

### Q5: 密码错误怎么办？

**A**: 
1. 检查输入的密码是否正确
2. 检查`.env`文件中的密码配置
3. 确认没有多余的空格
4. 重启服务器使配置生效

## 🔍 验证密码配置

### 检查密码是否已配置

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
password = os.getenv('CRAWL_PASSWORD', '')
if password:
    print('✅ 密码已配置')
    print(f'密码长度: {len(password)} 字符')
else:
    print('❌ 密码未配置')
    print('请在.env文件中设置 CRAWL_PASSWORD')
"
```

## 📝 示例配置

`.env`文件示例：

```bash
# 爬取密码配置
CRAWL_PASSWORD=MySecurePassword123!

# 其他配置...
QDRANT_URL=https://your-qdrant-instance.qdrant.io
QDRANT_API_KEY=your-api-key
GOOGLE_API_KEY=your-google-api-key
```

## ⚠️ 安全提醒

1. **不要将密码写入代码**
2. **不要将.env文件提交到Git**
3. **在生产环境使用HTTPS**
4. **限制服务器访问权限**
5. **定期更换密码**

## 📚 相关文档

- `.env.example` - 环境变量示例文件
- `CRAWL_PASSWORD_FEATURE.md` - 密码功能详细说明
- `web_server.py` - 服务器代码（密码验证逻辑）
