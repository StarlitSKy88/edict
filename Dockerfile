FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/{logs,metrics,cache,memory}

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV EDICT_ENV=production

# 暴露端口
EXPOSE 8080 3000

# 启动命令
CMD ["python", "main.py"]
