"""Chép dữ liệu từ PostgreSQL trên máy sang PostgreSQL trên máy chủ (bổ sung 20/10/2026,
viết lại an toàn hơn ở bản 3 cùng ngày theo báo cáo kiểm thử độc lập F01, F16).

Dùng khi đưa hệ thống lên mạng: không phải crawl lại, không phụ thuộc phiên bản
pg_dump/pg_restore giữa hai máy (máy bạn PostgreSQL 18, máy chủ có thể là bản khác).

    python chuyen_du_lieu.py --den "postgresql://...chuỗi kết nối EXTERNAL của máy chủ..."

Mặc định đọc nguồn từ DATABASE_URL trong backend\\.env (database trên máy bạn).

Làm gì:
  1. Kết nối hai bên rồi KIỂM TRA hai chuỗi kết nối có thực sự trỏ tới hai database khác nhau
     không (so sánh sau khi kết nối, không chỉ so chuỗi). Trùng thì dừng, không xóa gì.
  2. Tạo bảng ở đích nếu chưa có (không xóa bảng nào ở nguồn hay ở đích). Chép bảng thủ tục
     (guidance_documents) và lịch sử thao tác cán bộ (thao_tac_can_bo); bảng nào ở đích đã giống
     hệt nguồn thì bỏ qua bảng đó.
  3. Đọc nguồn trong MỘT ảnh chụp nhất quán, chỉ đọc.
  4. Ghi đích trong MỘT giao dịch: (xóa dữ liệu cũ của đích nếu có --xoa-dich) → chép các bảng
     giữ nguyên id → kiểm tra. Chỉ khi kiểm tra khớp mới lưu (commit). Lỗi ở bất kỳ bước nào thì
     đích quay về đúng như trước khi chạy. Bộ đếm id (PostgreSQL) chỉ được đặt lại SAU khi đã lưu.
  5. Kiểm tra: số bản ghi; mã băm SHA-256 của nội dung (mọi cột trừ thời điểm tạo/sửa); mã băm
     riêng của thời điểm tạo/sửa đã quy về giờ UTC. Cả ba phải trùng.
     Nhật ký tra cứu (search_logs) KHÔNG chép, trừ khi thêm --kem-nhat-ky.

An toàn: chỉ ĐỌC ở nguồn. Nếu bảng đích đã có dữ liệu thì dừng, trừ khi thêm --xoa-dich.
Nếu đích đã giống hệt nguồn thì báo và dừng, không xóa, không chép.
"""
import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import timezone
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import database, models  # noqa: E402

LO = 300
COT_THOI_GIAN = ("created_at", "updated_at")


class DungLai(Exception):
    """Lý do dừng có chủ đích (không phải lỗi chương trình)."""


def _url(u: str) -> str:
    return "postgresql://" + u[len("postgres://"):] if u.startswith("postgres://") else u


def _an(u: str) -> str:
    """Ẩn mật khẩu khi in chuỗi kết nối."""
    import re
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", u)


def _gia_tri(v):
    if hasattr(v, "isoformat"):
        if getattr(v, "tzinfo", None) is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v.isoformat()
    return v


def _bam(s: Session, model, cot):
    """(số dòng, SHA-256) của các cột `cot`, theo thứ tự id. Thời điểm quy về UTC."""
    h, n = hashlib.sha256(), 0
    for row in s.execute(select(*[getattr(model, c) for c in cot]).order_by(model.id)):
        h.update(json.dumps([_gia_tri(x) for x in row], ensure_ascii=False, sort_keys=True,
                            default=str).encode("utf-8"))
        n += 1
    return n, h.hexdigest()


def _dau_van_tay(s: Session, model, cot):
    noi_dung = [c for c in cot if c not in COT_THOI_GIAN]
    thoi_gian = ["id"] + [c for c in cot if c in COT_THOI_GIAN]
    n, h_nd = _bam(s, model, noi_dung)
    _, h_tg = _bam(s, model, thoi_gian)
    return n, h_nd, h_tg


def kiem_tra_khac_database(e_nguon, e_dich, s_nguon: Session, s_dich: Session, dau_nguon: str):
    """Dừng nếu hai kết nối cùng trỏ tới MỘT database, dù chuỗi kết nối viết khác nhau."""
    u1, u2 = e_nguon.url, e_dich.url
    if u1.get_backend_name() != u2.get_backend_name():
        return
    if u1.get_backend_name() == "sqlite":
        p1, p2 = u1.database or "", u2.database or ""
        if p1 in ("", ":memory:") or p2 in ("", ":memory:"):
            return
        if os.path.realpath(p1) == os.path.realpath(p2) or (
                os.path.exists(p1) and os.path.exists(p2) and os.path.samefile(p1, p2)):
            raise DungLai("Nguồn và đích là CÙNG một tệp database. Dừng, không xóa và không chép gì.")
        return
    if u1.get_backend_name() == "postgresql":
        # Kết nối nguồn mang một tên ứng dụng ngẫu nhiên; nếu phía đích nhìn thấy đúng kết nối đó
        # trong cùng database thì hai chuỗi kết nối là một database.
        thay = s_dich.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name = :a "
                                   "AND datname = current_database()"), {"a": dau_nguon}).scalar()
        if thay:
            raise DungLai("Nguồn và đích là CÙNG một database PostgreSQL (chuỗi kết nối viết khác nhau "
                          "nhưng trỏ cùng chỗ). Dừng, không xóa và không chép gì.")


def chep_bang(s_nguon: Session, s_dich: Session, model, cot) -> int:
    """Chép theo lô vào giao dịch đang mở của s_dich (KHÔNG commit ở đây)."""
    tong, cuoi = 0, -1
    while True:
        lo = s_nguon.execute(select(*[getattr(model, c) for c in cot]).where(model.id > cuoi)
                             .order_by(model.id).limit(LO)).all()
        if not lo:
            break
        s_dich.execute(model.__table__.insert(), [dict(zip(cot, r)) for r in lo])
        cuoi = lo[-1][0]
        tong += len(lo)
        print(f"  đã chép {tong} bản ghi (chưa lưu)", end="\r", flush=True)
    print()
    return tong


def chuyen(nguon: str, den: str, kem_nhat_ky=False, xoa_dich=False, sau_moi_bang=None) -> int:
    """Trả về 0 nếu chép đủ và khớp; ném DungLai nếu dừng có chủ đích."""
    nguon, den = _url(nguon), _url(den)
    if make_url(nguon) == make_url(den):
        raise DungLai("Nguồn và đích trùng nhau, dừng.")
    print("Nguồn:", _an(nguon))
    print("Đích :", _an(den))
    dau_nguon = "chuyen_du_lieu_" + uuid.uuid4().hex[:12]
    tuy_chon_nguon = {}
    if make_url(nguon).get_backend_name() == "postgresql":
        tuy_chon_nguon = {"connect_args": {"application_name": dau_nguon},
                          "execution_options": {"isolation_level": "REPEATABLE READ",
                                                "postgresql_readonly": True}}
    e_nguon = create_engine(nguon, **tuy_chon_nguon)
    e_dich = create_engine(den, pool_pre_ping=True)

    bang = [(models.GuidanceDocument, ["id", "procedure_code", "title", "agency", "category", "status",
                                       "search_text", "data", "created_at", "updated_at"]),
            # Sửa 21/10 bản 2 (N04): lịch sử thao tác của cán bộ là dữ liệu của sản phẩm, luôn chép theo.
            (models.ThaoTacCanBo, ["id", "luc", "tai_khoan", "hanh_dong", "id_thu_tuc", "ma_thu_tuc",
                                   "tieu_de", "chi_tiet"])]
    if kem_nhat_ky:
        bang.append((models.SearchLog, ["id", "kind", "query", "result_count", "top_percent", "top_code",
                                        "outcome", "duration_ms", "created_at"]))

    with Session(e_nguon) as sn, Session(e_dich) as sd:
        sn.execute(text("SELECT 1"))                      # mở kết nối nguồn trước để đích nhìn thấy
        kiem_tra_khac_database(e_nguon, e_dich, sn, sd, dau_nguon)
        sd.rollback()
        models.Base.metadata.create_all(e_dich)
        co_o_nguon = set(inspect(e_nguon).get_table_names())
        bang = [(m, c) for m, c in bang if m.__tablename__ in co_o_nguon]   # nguồn cũ chưa có bảng mới thì bỏ qua

        # Chốt dấu vân tay của nguồn trước khi đụng tới đích
        van_tay = {}
        for model, cot in bang:
            van_tay[model.__tablename__] = _dau_van_tay(sn, model, cot)

        # Sửa 21/10 bản 2 (N05): lập kế hoạch TỪNG BẢNG. Bảng nào ở đích đã giống hệt nguồn thì bỏ qua
        # bảng đó; bảng khác nguồn mà đích đã có dữ liệu thì cần --xoa-dich. Chỉ khi MỌI bảng đều giống
        # hệt mới báo “không cần chép”.
        can_chep = []
        for model, cot in bang:
            ten = model.__tablename__
            co_san = sd.scalar(select(func.count()).select_from(model))
            if not co_san and van_tay[ten][0] == 0:
                continue                                  # cả hai bên cùng rỗng
            if co_san and _dau_van_tay(sd, model, cot) == van_tay[ten]:
                print(f"  {ten}: đích đã giống hệt nguồn ({co_san} bản ghi), bỏ qua bảng này.")
                continue
            if co_san and not xoa_dich:
                raise DungLai(f"Bảng {ten} ở đích đã có {co_san} bản ghi khác nguồn. Thêm --xoa-dich nếu muốn thay "
                              "bằng dữ liệu nguồn (chỉ thay ở ĐÍCH, và chỉ khi chép xong, khớp mới lưu).")
            can_chep.append((model, cot, bool(co_san)))
        sd.rollback()
        if not can_chep:
            raise DungLai("Mọi bảng ở đích đã giống hệt nguồn. Không cần chép lại; không xóa gì.")

        # Một giao dịch duy nhất ở đích
        loi = 0
        try:
            for model, cot, co_san in can_chep:
                ten = model.__tablename__
                if co_san:
                    sd.execute(model.__table__.delete())
                print(f"Chép bảng {ten}…")
                n = chep_bang(sn, sd, model, cot)
                if sau_moi_bang:
                    sau_moi_bang(ten)                     # dùng cho kiểm thử: giả lập lỗi giữa chừng
                n1, nd1, tg1 = van_tay[ten]
                n2, nd2, tg2 = _dau_van_tay(sd, model, cot)
                dung = n1 == n2 == n and nd1 == nd2 and tg1 == tg2
                loi += 0 if dung else 1
                print(f"  {ten}: nguồn {n1}, đích {n2}; nội dung SHA-256 {'TRÙNG' if nd1 == nd2 else 'KHÁC'} "
                      f"({nd1[:12]}…); thời điểm {'TRÙNG' if tg1 == tg2 else 'KHÁC'}")
            if loi:
                sd.rollback()
                print("KẾT QUẢ: CÓ BẢNG KHÔNG KHỚP. Đã hủy toàn bộ thay đổi ở đích; đích giữ nguyên như trước.")
                return 1
            sd.commit()
        except BaseException:
            sd.rollback()
            print("\nLỗi giữa chừng: đã hủy toàn bộ thay đổi ở đích; đích giữ nguyên như trước khi chạy.")
            raise
        # Sửa 21/10 bản 2 (N06): setval của PostgreSQL KHÔNG hoàn tác được khi rollback, nên chỉ đặt lại
        # bộ đếm id SAU khi dữ liệu đã lưu xong. Lệnh này chạy lại bao nhiêu lần cũng cho cùng kết quả.
        if sd.bind.dialect.name == "postgresql":
            for model, _, _ in can_chep:
                ten = model.__tablename__
                sd.execute(text(f"SELECT setval(pg_get_serial_sequence('{ten}', 'id'), "
                                f"COALESCE((SELECT MAX(id) FROM {ten}), 1))"))
            sd.commit()
    print("KẾT QUẢ: CHÉP ĐỦ VÀ KHỚP")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nguon", default=database.DATABASE_URL, help="mặc định: DATABASE_URL trong .env")
    ap.add_argument("--den", required=True, help="chuỗi kết nối PostgreSQL ở máy chủ")
    ap.add_argument("--kem-nhat-ky", action="store_true", help="chép cả bảng nhật ký tra cứu")
    ap.add_argument("--xoa-dich", action="store_true",
                    help="thay dữ liệu đang có trong bảng ĐÍCH (trong cùng giao dịch, chỉ lưu khi khớp)")
    a = ap.parse_args()
    try:
        sys.exit(chuyen(a.nguon, a.den, a.kem_nhat_ky, a.xoa_dich))
    except DungLai as e:
        print("DỪNG:", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
