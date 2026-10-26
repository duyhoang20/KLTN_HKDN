# Đóng gói hệ thống để chạy trên máy chủ (bổ sung 20/10/2026).
# Dùng được cho Render, Railway, Koyeb, Fly.io hoặc máy chủ riêng có Docker.
# Database KHÔNG nằm trong ảnh: máy chủ đọc chuỗi kết nối từ biến môi trường DATABASE_URL.
FROM python:3.10-slim

ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
COPY frontend frontend

WORKDIR /app/backend
# Dịch vụ đám mây cấp cổng qua biến PORT; chạy trên máy thì mặc định 8000.
# Không bật --forwarded-allow-ips='*' (tin mọi proxy): IP người dùng do ứng dụng tự đọc từ cuối
# X-Forwarded-For theo biến SO_PROXY_TIN_CAY (backend/app/mang.py), sửa 21/10 bản 2.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
