"""Đánh giá tra cứu trên dữ liệu thật, phiên bản ABC-20260924-1.

A: tối đa 25 âm tiết đầu của tên thủ tục.
B: một đoạn liền mạch khoảng 60% tên, tối thiểu 4 âm tiết.
C: 3–5 âm tiết mở đầu, chỉ để tham khảo.

Giữ truy vấn không dấu để lấy mốc A/B/C theo tài liệu bàn giao.
Chưa đo truy vấn có dấu, đồng nghĩa hoặc chất lượng trả lời RAG.
Đáp án là ID thủ tục gốc; tên/đoạn tên trùng có thể có nhiều đáp án hợp lý.
Không thay đổi search.py, không ghi dữ liệu vào cơ sở dữ liệu.

Chạy từ backend:
    python danh_gia.py 500 --luu bao_cao_nen_ABC_500.txt
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import unicodedata


PHIEN_BAN = "ABC-20260924-1"
SEED = 20260915
THU_MUC = Path(__file__).resolve().parent


def chuan_hoa_de(text):
    """Cố định chuẩn hóa bộ đề, độc lập với thay đổi thuật toán tra cứu.

Tương đương normalize() trong search.py đã đối chiếu ngày 24/09/2026.
    """
    text = (text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sinh_truy_van(title, kieu="day_du", rng=None):
    """Cắt đoạn liên tiếp, không chọn âm tiết theo trọng số tìm kiếm."""
    if rng is None:
        rng = random.Random(SEED)
    syl = chuan_hoa_de(title).split()
    if len(syl) < 5:
        return None
    if kieu == "day_du":
        return " ".join(syl[:25])
    if kieu == "mot_doan":
        n = max(4, int(len(syl) * 0.6))
        i = rng.randint(0, len(syl) - n)
        return " ".join(syl[i:i + n])
    if kieu == "chung_chung":
        return " ".join(syl[:rng.randint(3, min(5, len(syl)))])
    raise ValueError(f"Kiểu truy vấn không được hỗ trợ: {kieu}")


def ma_json(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ma_file(path):
    # Thống nhất LF/CRLF để cùng mã nguồn cho cùng dấu kiểm tra trên Windows/Linux.
    source = Path(path).read_text(encoding="utf-8-sig")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def tao_bo_de(docs, so_mau, kieu, seed):
    rng = random.Random(seed)
    mau = rng.sample(docs, min(so_mau * 3, len(docs)))
    de = []
    for doc in mau:
        query = sinh_truy_van(doc.title or "", kieu, rng)
        if query:
            de.append((doc, query))
        if len(de) >= so_mau:
            break
    return de


def so_duong(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("Số mẫu phải lớn hơn 0.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("so_mau", nargs="?", type=so_duong, default=300)
    parser.add_argument("--luu", type=Path, help="Đường dẫn báo cáo UTF-8")
    args = parser.parse_args()

    if args.luu and args.luu.suffix.lower() != ".txt":
        parser.error("File báo cáo phải có đuôi .txt để tránh ghi đè mã nguồn.")

    # Chỉ import ứng dụng khi thực sự chạy đánh giá; --help không cần DB.
    sys.path.insert(0, str(THU_MUC))
    from app.database import SessionLocal
    from app import models, search as search_module

    dong = []

    def ra(s=""):
        dong.append(s)
        print(s)

    db = SessionLocal()
    try:
        docs = (db.query(models.GuidanceDocument)
                .filter(models.GuidanceDocument.status == "published")
                .order_by(models.GuidanceDocument.id).all())
        if not docs:
            print("Chưa có thủ tục published trong cơ sở dữ liệu; không tạo báo cáo.")
            return 1

        ra("=" * 76)
        ra("ĐÁNH GIÁ CHẤT LƯỢNG TRA CỨU — A/B/C")
        ra("=" * 76)
        ra(f"Phiên bản bộ đo : {PHIEN_BAN}")
        ra(f"Kho dữ liệu     : {len(docs):,} thủ tục".replace(",", "."))
        ra(f"Số mẫu yêu cầu  : {args.so_mau} cho mỗi nhóm")
        ra(f"Seed gốc        : {SEED}; thứ tự kho: ID tăng dần")
        ra(f"SHA256 bộ đo    : {ma_file(__file__)}")
        ra(f"SHA256 search.py: {ma_file(search_module.__file__)}")
        ra("SHA256 kho tra cứu: " + ma_json([
            [d.id, d.procedure_code, d.title, d.category, d.status] for d in docs
        ]))
        ra("Dấu kiểm tra kho chỉ xét trường dùng cho xếp hạng và xác định đáp án.")
        ra("Đánh giá bằng ID thủ tục gốc; các truy vấn đều KHÔNG DẤU.")
        ra("Tên hoặc đoạn tên trùng có thể có nhiều kết quả hợp lý.")
        ra("'Không thấy' = không thấy ID gốc trong kết quả search() trả về,")
        ra("không đồng nghĩa với hệ thống không trả kết quả nào.")
        ra("Chỉ so sánh trước/sau khi bộ đo, kho và bộ đề từng nhóm giống nhau.")
        ra()

        print("Đang xây chỉ mục...", flush=True)
        search_module.xay_chi_muc(docs)

        nhom = [
            ("A", "day_du", "GÕ NGUYÊN TÊN THỦ TỤC",
             "Giới hạn 25 âm tiết đầu; không bảo đảm đáp án duy nhất.", SEED),
            ("B", "mot_doan", "GÕ MỘT ĐOẠN TRONG TÊN",
             "Đoạn liên tiếp khoảng 60% tên; nhóm chính để so sánh.", SEED + 1),
            ("C", "chung_chung", "GÕ CỤM MỞ ĐẦU CHUNG CHUNG",
             "3–5 âm tiết mở đầu; chỉ tham khảo, thường không có đáp án duy nhất.", SEED + 2),
        ]
        for ma, kieu, ten, ghi_chu, seed in nhom:
            de = tao_bo_de(docs, args.so_mau, kieu, seed)
            tong = len(de)
            ra("-" * 76)
            ra(f"{ma}. {ten} ({tong} truy vấn)")
            ra(ghi_chu)
            ra(f"SHA256 bộ đề {ma}: " + ma_json([[d.id, q] for d, q in de]))
            if not tong:
                ra("Không đủ tiêu đề có ít nhất 5 âm tiết; không tính chỉ số.")
                continue
            if tong < args.so_mau:
                ra(f"Chỉ có {tong} truy vấn hợp lệ trong mẫu; dùng mẫu số này.")

            top1 = top5 = khong_thay = tong_kq = 0
            tong_nghich_dao = 0.0
            vi_du = []
            for stt, (doc, query) in enumerate(de, 1):
                kq = search_module.search(query, docs)
                tong_kq += len(kq)
                vt = next((i for i, (d, _, _) in enumerate(kq, 1)
                           if d.id == doc.id), None)
                if vt == 1:
                    top1 += 1
                if vt is not None:
                    top5 += int(vt <= 5)
                    tong_nghich_dao += 1 / vt
                else:
                    khong_thay += 1
                if vt != 1 and len(vi_du) < 15:
                    dung_dau = kq[0][0] if kq else None
                    vi_du.append((doc, query, vt, len(kq), dung_dau))
                if stt % 50 == 0 or stt == tong:
                    print(f"  Đang đo nhóm {ma}: {stt}/{tong}", flush=True)

            ra(f"Top-1                           : {top1/tong*100:.1f}% ({top1}/{tong})")
            ra(f"Top-5                           : {top5/tong*100:.1f}% ({top5}/{tong})")
            ra(f"MRR (trung bình nghịch đảo hạng): {tong_nghich_dao/tong:.6f}")
            ra(f"Không tìm thấy đáp án           : {khong_thay/tong*100:.1f}% ({khong_thay}/{tong})")
            ra(f"Số kết quả trung bình           : {tong_kq/tong:.2f}")
            if ma in ("A", "B") and vi_du:
                ra(f"Ví dụ chưa đứng đầu ở nhóm {ma} (tối đa 15):")
                for doc, query, vt, so_kq, dung_dau in vi_du:
                    ra(f"  Truy vấn : {query}")
                    ra(f"  Đáp án   : ID={doc.id}; mã={doc.procedure_code or '(trống)'}")
                    ra(f"  Tên gốc  : {doc.title}")
                    ra(f"  Thứ hạng : {vt if vt is not None else 'không thấy'}; {so_kq} kết quả")
                    if dung_dau:
                        ra(f"  Đứng đầu : ID={dung_dau.id}; {dung_dau.title}")
                    ra()
            ra()
    finally:
        db.close()

    if args.luu:
        args.luu.write_text("\n".join(dong) + "\n", encoding="utf-8")
        print(f"Đã ghi báo cáo vào: {args.luu.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
