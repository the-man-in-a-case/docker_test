# 使用官方 Python 镜像作为基础镜像
FROM python:3.10-alpine

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*

# 安装 Python 依赖
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir django==5.2.5; \
    fi

# 复制项目文件
COPY . .

# 创建静态文件目录
# RUN mkdir -p /app/staticfiles

# 运行数据库迁移
RUN python manage.py migrate

# 收集静态文件
# RUN python manage.py collectstatic --noinput

# 暴露端口 8000
EXPOSE 8000

# 设置启动命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]