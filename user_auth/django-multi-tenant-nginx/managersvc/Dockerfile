FROM python:3.10-alpine
WORKDIR /app
COPY shared /app/shared
COPY managersvc /app/managersvc
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
# 设置Python路径
ENV PYTHONPATH=/app
WORKDIR /app/managersvc

ENV DJANGO_SETTINGS_MODULE=managersvc.settings
# 启两个进程：Django Web 与 Celery Worker 用不同容器（见 k8s yaml），这里只提供镜像
CMD ["tail", "-f", "/dev/null"]
# CMD ["gunicorn", "-b", "0.0.0.0:8000", "managersvc.wsgi:application", "--access-logfile", "-", "--error-logfile", "-", "--workers", "2", "--threads", "4"]
# CMD ["gunicorn", "-b", "0.0.0.0:8000", "authsvc.wsgi:application", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--log-level=info", "--workers", "2", "--threads", "4"]
