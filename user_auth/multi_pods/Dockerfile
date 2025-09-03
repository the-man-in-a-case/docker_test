FROM python:3.10-alpine

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY manager.py /app/manager.py

# 设置环境变量默认值
ENV POD_NAMESPACE=default
ENV DEPLOYMENT_NAME=manager-deployment

# 设置入口点
CMD ["python", "/app/manager.py"]