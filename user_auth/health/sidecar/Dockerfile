FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install httpx
COPY app.py .

EXPOSE 9000
CMD ["tail", "-f", "/dev/null"]
# CMD ["python", "app.py"]
