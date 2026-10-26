"""
Kiểm tra chất lượng tra cứu trên dữ liệu thật.

In các kết quả search() trả về và chia theo nhóm điểm để soi thủ công.
Hàm vẫn áp dụng ngưỡng, giới hạn 60 kết quả chính hoặc 8 gợi ý; đây không
phải danh sách mọi ứng viên trước khi cắt ngưỡng. Không thay thế danh_gia.py.

Cách dùng:
    python test_search.py                       chạy bộ truy vấn mẫu
    python test_search.py "hộ khẩu"             chạy một truy vấn
    python test_search.py "a" "b"               chạy nhiều truy vấn
    python test_search.py --yeu                 CHỈ hiện nhóm yếu (dễ soi lỗi)
    python test_search.py --luu ketqua.txt      ghi kết quả ra file để xem lại

Không cần bật server, script nối thẳng vào cơ sở dữ liệu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app import models
from app.search import search

TRUY_VAN_MAU = [
    "đăng ký hộ khẩu",
    "đăng ký khai sinh",
    "cấp hộ chiếu",
    "giấy phép lái xe",
    "lý lịch tư pháp",
    "vi phạm giao thông",
    "phạm vi bảo vệ",          # phải ra kết quả KHÁC HẲN "vi phạm giao thông"
    "đăng ký kết hôn",
    "căn cước công dân",
    "đăng ký kinh doanh",
    "dang ky khai sinh",       # gõ không dấu
]

# Chia nhóm theo phần trăm liên quan
NHOM = [
    (90, 100, "RẤT SÁT   (90-100%)"),
    (70, 89, "KHÁ SÁT   (70-89%)"),
    (50, 69, "TRUNG BÌNH (50-69%)"),
    (0, 49, "YẾU — soi kỹ nhóm này (<50%)"),
]


def main():
    args = list(sys.argv[1:])
    chi_yeu = "--yeu" in args
    if chi_yeu:
        args.remove("--yeu")

    file_luu = None
    if "--luu" in args:
        i = args.index("--luu")
        file_luu = args[i + 1] if i + 1 < len(args) else "ketqua_tra_cuu.txt"
        del args[i:i + 2]

    truy_van = args if args else TRUY_VAN_MAU
    dong = []

    def ra(s=""):
        dong.append(s)
        print(s)

    db = SessionLocal()
    try:
        docs = (db.query(models.GuidanceDocument)
                .filter(models.GuidanceDocument.status == "published")
                .order_by(models.GuidanceDocument.id).all())
        ra(f"Tra cứu trên {len(docs):,} thủ tục".replace(",", "."))
        if chi_yeu:
            ra("(Chế độ CHỈ HIỆN NHÓM YẾU)")
        ra()

        for q in truy_van:
            kq = search(q, docs)
            ra("=" * 78)
            ra(f"  TRUY VẤN: {q}   →  {len(kq)} kết quả")

            # Thống kê nhanh theo nhóm
            dem = []
            for lo, hi, ten in NHOM:
                n = sum(1 for _, _, p in kq if lo <= p <= hi)
                if n:
                    dem.append(f"{ten.split('(')[0].strip()}: {n}")
            if dem:
                ra("  " + " | ".join(dem))
            ra("=" * 78)

            if not kq:
                ra("    (không có kết quả)")
                ra()
                continue

            for lo, hi, ten_nhom in NHOM:
                trong_nhom = [(d, p) for d, _, p in kq if lo <= p <= hi]
                if not trong_nhom:
                    continue
                if chi_yeu and lo >= 50:
                    continue
                ra(f"\n  --- {ten_nhom} · {len(trong_nhom)} kết quả ---")
                for doc, pt in trong_nhom:
                    ten = doc.title if len(doc.title) <= 88 else doc.title[:85] + "..."
                    ra(f"  {pt:3d}%  {ten}")
                    ra(f"        {doc.agency or '—'} · {doc.category or '—'}")
            ra()
    finally:
        db.close()

    if file_luu:
        with open(file_luu, "w", encoding="utf-8") as f:
            f.write("\n".join(dong))
        print(f"\nĐã ghi kết quả vào: {file_luu}")


if __name__ == "__main__":
    main()
