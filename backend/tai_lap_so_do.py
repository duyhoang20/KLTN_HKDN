"""Chạy lại các script đánh giá trên bộ dữ liệu mẫu, KHÔNG cần PostgreSQL (bổ sung 26/10/2026).

    python tai_lap_so_do.py                      # = danh_gia.py 500 (bộ đo A/B/C trong báo cáo)
    python tai_lap_so_do.py danh_gia_tu_nhien.py # chạy script đánh giá khác, kèm tham số của nó

Script dùng tệp SQLite backend/du_lieu_demo.db (tự tạo và nạp dữ liệu mẫu nếu chưa có,
giống chay_demo.py), rồi chạy script đánh giá được chỉ định trên đó. Kho mẫu chính là kho
9.451 thủ tục đã dùng để đo, nên bộ A/B/C cho đúng các con số trong khóa luận
(Top-1 bộ A 90,8%, bộ B 72,0%; mã băm kho 2319b44b...).
"""
import os
import runpy
import sys
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
TEP_DB = THU_MUC / "du_lieu_demo.db"


def main():
    tham_so = sys.argv[1:] or ["danh_gia.py", "500"]
    script = THU_MUC / tham_so[0]
    if not script.is_file():
        sys.exit(f"Không thấy {tham_so[0]} trong thư mục backend.")

    os.environ["DATABASE_URL"] = "sqlite:///" + TEP_DB.as_posix()
    import sqlalchemy.dialects.postgresql as _pg
    from sqlalchemy import JSON
    _pg.JSONB = JSON                      # SQLite không có JSONB; chỉ áp dụng trong tiến trình này

    sys.path.insert(0, str(THU_MUC))
    from app.database import SessionLocal, engine
    from app import models
    import nap_du_lieu_mau
    assert engine.dialect.name == "sqlite"
    nap_du_lieu_mau.nap(engine, SessionLocal, models, in_ra=lambda s: print(s))

    sys.argv = [str(script)] + tham_so[1:]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
