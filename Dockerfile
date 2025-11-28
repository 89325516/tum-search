# 1. 使用官方 Python 基础镜像
FROM python:3.9-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 (安装 Rust 编译器和构建工具)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# 4. 复制依赖文件并安装 Python 库
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制整个项目代码
COPY . .

# 6. 编译你的 Rust 引擎
# 进入 Rust 项目目录，使用 maturin 编译并安装到当前 Python 环境
WORKDIR /app/visual_rank_engine
RUN maturin build --release
# 安装生成的 .whl 文件
RUN pip install target/wheels/*.whl

# 7. 回到应用根目录
WORKDIR /app

# 8. 创建必要的文件夹 (防止运行时报错)
RUN mkdir -p temp_uploads static mock_data

# 9. 暴露端口 (Hugging Face 默认监听 7860)
EXPOSE 7860

# 10. 创建非 root 用户 (Hugging Face Spaces 安全要求)
RUN useradd -m -u 1000 user

# 11. 设置目录权限
RUN chown -R user:user /app

# 12. 切换到非 root 用户
USER user

# 13. 启动命令
# 注意：Hugging Face 要求监听 7860 端口
CMD ["uvicorn", "web_server:app", "--host", "0.0.0.0", "--port", "7860"]