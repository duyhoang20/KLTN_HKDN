"""Chạy thử toàn bộ hệ thống KHÔNG cần cài PostgreSQL (bổ sung 26/10/2026).

    python chay_demo.py                  # mở http://127.0.0.1:8000
    python chay_demo.py --cong 8080      # đổi cổng

Lần đầu chạy, script tạo tệp SQLite backend/du_lieu_demo.db và nạp bộ dữ liệu mẫu
(9.451 thủ tục, 20 thủ tục có nội dung chi tiết; xem nap_du_lieu_mau.py). Các lần sau
dùng lại tệp đó. Muốn làm lại từ đầu thì xóa du_lieu_demo.db.

Chế độ này dành cho xem thử và chấm bài trên máy cá nhân. Bản chạy thật dùng PostgreSQL
(xem README, mục "Chạy đầy đủ với PostgreSQL"). Khu vực cán bộ chỉ mở khi đã đặt
QUAN_TRI_TAI_KHOAN và QUAN_TRI_MAT_KHAU trong backend/.env.
"""
import argparse
import os
import sys
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
TEP_DB = THU_MUC / "du_lieu_demo.db"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cong", type=int, default=8000, help="cổng máy chủ (mặc định 8000)")
    a = ap.parse_args()

    # Đặt TRƯỚC khi nạp ứng dụng: luôn dùng tệp SQLite riêng, không bao giờ chạm database thật
    # dù backend/.env có DATABASE_URL.
    os.environ["DATABASE_URL"] = "sqlite:///" + TEP_DB.as_posix()

    # SQLite không có kiểu JSONB của PostgreSQL; dùng JSON thường trong tiến trình này
    # (cùng cách bộ kiểm thử kiem_thu_api.py đang làm).
    import sqlalchemy.dialects.postgresql as _pg
    from sqlalchemy import JSON
    _pg.JSONB = JSON

    sys.path.insert(0, str(THU_MUC))
    from app.database import SessionLocal, engine
    from app import models
    import nap_du_lieu_mau

    assert engine.dialect.name == "sqlite"
    if not TEP_DB.exists() or TEP_DB.stat().st_size == 0:
        print("Lần đầu chạy: đang nạp dữ liệu mẫu vào", TEP_DB.name, "...")
    nap_du_lieu_mau.nap(engine, SessionLocal, models, in_ra=lambda s: print(" ", s))

    if not (os.getenv("QUAN_TRI_TAI_KHOAN") and os.getenv("QUAN_TRI_MAT_KHAU")):
        print("  Khu vực cán bộ đang khóa: đặt QUAN_TRI_TAI_KHOAN và QUAN_TRI_MAT_KHAU trong backend/.env để mở.")

    import uvicorn
    from app.main import app
    print(f"\nMở trình duyệt: http://127.0.0.1:{a.cong}/  (Ctrl+C để dừng)\n")
    uvicorn.run(app, host="127.0.0.1", port=a.cong)


if __name__ == "__main__":
    main()
