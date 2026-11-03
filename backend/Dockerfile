# 后端镜像：FastAPI + Python 3.12
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/installdeps -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /installdeps /usr/local
COPY app ./app

# 镜像默认生产模式，不内置数据库口令。docker-compose 的演示栈会覆盖 APP_ENV 与 DATABASE_URL。
ENV APP_ENV=production \
    DEEPSEEK_API_KEY="" \
    MILVUS_HOST="milvus" \
    UPLOAD_DIR="/data/uploads" \
    MEDIA_STORAGE=db \
    MEDIA_FS_ROOT=/data/uploads/media

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]