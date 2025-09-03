FROM python:3.10-alpine
WORKDIR /app
COPY shared /app/shared
COPY authsvc /app/authsvc
COPY shared/requirements.txt /app/requirements.txt
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖：
# - pkg-config：用于编译时查找库文件
# - default-libmysqlclient-dev：MySQL开发库
# - build-essential：提供编译工具（gcc等）
# - && rm -rf /var/lib/apt/lists/*：清理缓存，减小镜像体积
RUN apk add --no-cache \
    pkgconf \
    mysql-dev \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn
ENV PYTHONPATH=/app
WORKDIR /app/authsvc
ENV DJANGO_SETTINGS_MODULE=authsvc.settings
# CMD ["gunicorn", "-b", "0.0.0.0:8000", "authsvc.wsgi:application", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--log-level=info", "--workers", "2", "--threads", "4"]
# CMD ["tail", "-f", "/dev/null"]
# 复制启动脚本并设置执行权限
COPY authsvc/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# 安装netcat-openbsd用于数据库连接检查
RUN apk add --no-cache netcat-openbsd

CMD ["/app/startup.sh"]