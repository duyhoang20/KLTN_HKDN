"""Nạp bộ dữ liệu mẫu đi kèm mã nguồn vào cơ sở dữ liệu (bổ sung 26/10/2026).

Dùng khi KHÔNG có tài khoản API của đơn vị cấp dữ liệu, để vẫn chạy được hệ thống
và tái lập các phép đo tra cứu trên đúng kho đã dùng trong khóa luận.

    python nap_du_lieu_mau.py              # nạp vào DATABASE_URL trong backend/.env

Dữ liệu nạp vào:
  * du_lieu_mau/kho_9451_thu_tuc.json: 9.451 thủ tục (mã, tên, cơ quan, lĩnh vực) của
    bản xuất ngày 24/09/2026, giữ nguyên id gốc để thứ tự xếp hạng khi bằng điểm
    giống hệt lúc đo. Đây là kho dùng cho mọi số đo tra cứu trong báo cáo.
  * du_lieu_mau/mau_21_thu_tuc_du_lieu_chi_tiet.json: nội dung chi tiết đầy đủ
    (hồ sơ, lệ phí, thời hạn...) của 20 thủ tục có trong kho trên. Thủ tục thứ 21
    (đất đai, UBND tỉnh Vĩnh Long) nằm ngoài kho đo, chỉ nạp khi thêm --them-thu-tuc-ngoai-kho.

Các thủ tục còn lại chỉ có tên, cơ quan và lĩnh vực: tra cứu chạy đầy đủ, nhưng trang
chi tiết và trợ lý chỉ có nội dung đầy đủ ở 20 thủ tục trên.

An toàn: script CHỈ nạp vào bảng thủ tục đang TRỐNG. Nếu bảng đã có dữ liệu, script
dừng và không sửa, không xóa gì.
"""
import argparse
import json
import sys
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
GOC = THU_MUC.parent
KHO = GOC / "du_lieu_mau" / "kho_9451_thu_tuc.json"
CHI_TIET = GOC / "du_lieu_mau" / "mau_21_thu_tuc_du_lieu_chi_tiet.json"


def _du_lieu_toi_thieu(ban_ghi):
    """Phần data cho thủ tục chỉ có tên: chỉ ghi những gì bản xuất thật sự có."""
    return {
        "MaThuTucHanhChinh": ban_ghi["procedure_code"],
        "TenThuTuc": ban_ghi["title"],
        "CoQuanBanHanh": {"TenCoQuanBanHanh": ban_ghi.get("agency") or ""},
        "LinhVuc": {"TenLinhVuc": ban_ghi.get("category") or ""},
        "GhiChuDuLieuMau": "Bản dữ liệu mẫu chỉ có mã, tên, cơ quan và lĩnh vực của thủ tục này.",
    }


def nap(engine, SessionLocal, models, them_ngoai_kho=False, in_ra=print):
    """Nạp dữ liệu mẫu. Trả về số thủ tục đã nạp; 0 nếu bảng đã có dữ liệu."""
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        da_co = db.query(models.GuidanceDocument).count()
        if da_co:
            in_ra(f"Bảng thủ tục đã có {da_co} bản ghi: không nạp dữ liệu mẫu (không sửa, không xóa gì).")
            return 0

        kho = json.loads(KHO.read_text(encoding="utf-8"))
        chi_tiet = {x["procedure_code"]: x for x in json.loads(CHI_TIET.read_text(encoding="utf-8"))}
        ds = kho["documents"]
        assert len(ds) == kho["count"], "Tệp kho bị thiếu bản ghi"

        so_chi_tiet = 0
        for r in ds:
            ct = chi_tiet.pop(r["procedure_code"], None)
            if ct:
                so_chi_tiet += 1
            db.add(models.GuidanceDocument(
                id=r["id"],
                procedure_code=r["procedure_code"],
                title=r["title"],
                agency=r.get("agency"),
                category=r.get("category"),
                status=r.get("status") or "published",
                search_text=f'{r["title"]} {r.get("category") or ""}'.strip(),
                data=ct["data"] if ct else _du_lieu_toi_thieu(r),
            ))
        tong = len(ds)
        if them_ngoai_kho:
            id_tiep = max(r["id"] for r in ds) + 1
            for ma, ct in chi_tiet.items():
                d = ct["data"]
                db.add(models.GuidanceDocument(
                    id=id_tiep, procedure_code=ma, title=ct["title"],
                    agency=(d.get("CoQuanBanHanh") or {}).get("TenCoQuanBanHanh"),
                    category=(d.get("LinhVuc") or {}).get("TenLinhVuc"),
                    status="published", search_text=ct["title"], data=d,
                ))
                id_tiep += 1
                tong += 1
                so_chi_tiet += 1
        db.commit()

        # PostgreSQL: đưa bộ đếm id lên sau id lớn nhất, để hướng dẫn cán bộ soạn mới không trùng id.
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(text("SELECT setval(pg_get_serial_sequence('guidance_documents', 'id'), "
                            "(SELECT MAX(id) FROM guidance_documents))"))
            db.commit()
        in_ra(f"Đã nạp {tong} thủ tục, trong đó {so_chi_tiet} thủ tục có nội dung chi tiết đầy đủ.")
        return tong
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--them-thu-tuc-ngoai-kho", action="store_true",
                    help="nạp thêm thủ tục mẫu không thuộc kho 9.451 (làm số đo khác báo cáo một chút)")
    a = ap.parse_args()
    sys.path.insert(0, str(THU_MUC))
    from app.database import SessionLocal, engine
    from app import models
    print(f"Cơ sở dữ liệu: {engine.url.render_as_string(hide_password=True)}")
    nap(engine, SessionLocal, models, them_ngoai_kho=a.them_thu_tuc_ngoai_kho)


if __name__ == "__main__":
    main()
