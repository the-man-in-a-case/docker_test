FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# 将你的整个 Django 项目拷贝进来（此处假设上一级就是项目根）
COPY . .

EXPOSE 8000
CMD ["tail", "-f", "/dev/null"]
# CMD ["gunicorn", "happ.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
