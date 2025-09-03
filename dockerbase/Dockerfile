# 使用 Python 3.10-alpine 作为基础镜像
FROM python:3.10-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量，避免 Python 写入 pyc 文件和缓冲输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # 设置 MySQL 客户端环境变量
    MYSQLCLIENT_CFLAGS="-I/usr/include/mysql" \
    MYSQLCLIENT_LDFLAGS="-L/usr/lib -lmysqlclient"

# 配置Alpine仓库
RUN echo "https://dl-cdn.alpinelinux.org/alpine/v3.21/main" > /etc/apk/repositories && \
    echo "https://dl-cdn.alpinelinux.org/alpine/v3.21/community" >> /etc/apk/repositories

# 安装 MySQL 客户端依赖和构建工具
RUN apk add --no-cache mariadb-connector-c-dev gcc musl-dev supervisor

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY core/ /app/core/

# 设置文件权限
RUN chmod -R 755 /app

# 创建 supervisord 配置文件目录并复制配置
RUN mkdir -p /etc/supervisor/conf.d
COPY supervisord.conf /etc/supervisor/conf.d/

# 暴露 Django 服务端口
EXPOSE 8000

# 使用 supervisord 启动服务
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]