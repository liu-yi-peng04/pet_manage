# 后端镜像：FastAPI + Python 3.12
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/installdeps -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /installdeps /usr/local
COPY app ./app

ENV DEEPSEEK_API_KEY="" \
    DATABASE_URL="mysql://root:123456@mysql:3306/ai_kb" \
    MILVUS_HOST="milvus" \
    UPLOAD_DIR="/data/uploads"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]