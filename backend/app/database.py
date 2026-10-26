import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/guidance_db",
)

# Một số dịch vụ đám mây cấp chuỗi kết nối dạng "postgres://"; SQLAlchemy 2 chỉ nhận "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

# pool_pre_ping: máy chủ database trên mây hay cắt kết nối rảnh; kiểm tra trước khi dùng để
# không trả lỗi 500 cho lượt truy cập đầu sau một lúc yên lặng.
engine = create_engine(DATABASE_URL, **({} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency dùng trong FastAPI để lấy 1 phiên làm việc với DB cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
