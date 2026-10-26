"""Đánh giá tra cứu trên CÂU HỎI TỰ NHIÊN có gán nhãn, phiên bản TN-20260929-1.

Bổ sung cho danh_gia.py (A/B/C). Bộ A/B/C cắt truy vấn từ chính tên thủ tục
nên không đo được từ đệm ("cần những gì"), đồng nghĩa ("sổ đỏ"), cách nói đời
thường, và KHÔNG đo được việc từ chối câu hỏi ngoài phạm vi. Bộ này đo cả hai
chiều: tìm đúng câu trong phạm vi, và trả rỗng với câu ngoài phạm vi.

Nguồn đề: ../bo_de_tu_nhien/bo_de_tu_nhien.csv. Cột ma_thu_tuc_dung:
    - một hoặc nhiều mã thủ tục đúng, cách nhau bằng dấu chấm phẩy;
    - KHONG_CO nếu kho không có thủ tục phù hợp (kết quả mong muốn: rỗng);
    - để trống nếu chưa gán.
Gán nhãn theo MÃ thủ tục, không theo ID, vì ID đổi khi tạo lại bảng.

KIỂM TRA ĐẦU VÀO NGHIÊM NGẶT. Mọi lỗi nhãn làm bộ đo DỪNG (mã thoát 2) và liệt
kê đủ lỗi, không âm thầm bỏ qua — vì bỏ qua một câu khó do gõ sai mã sẽ làm
chỉ số đẹp lên giả tạo. Các lỗi bị chặn: thiếu cột, bộ đề rỗng, loại câu lạ,
STT hoặc câu hỏi trùng, dòng thiếu câu hỏi, mã không có trong kho (kèm gợi ý
khi Excel làm hỏng mã), KHONG_CO đi cùng mã, câu "ngoai_pham_vi" có mã.

Chỉ số:
    Trong phạm vi (câu có mã): Top-1, Top-5, MRR, trả về rỗng, lạc đề
        (có kết quả nhưng không có mã đúng), số kết quả trung bình.
    Ngoài phạm vi (câu KHONG_CO): tỉ lệ TỪ CHỐI ĐÚNG (trả rỗng), và với câu
        trả lời sai thì phần trăm cao nhất đã hiển thị — phần trăm cao trên
        kết quả sai nguy hiểm hơn phần trăm thấp.
    Không cần nhãn: tỉ lệ trả về rỗng trên toàn bộ.
Phần trăm luôn tính trên đúng số câu của nhóm; nhóm rỗng thì ghi "không có câu".

Chạy từ backend:
    python danh_gia_tu_nhien.py --luu bao_cao_tu_nhien.txt
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bo_doc_csv import LoiBoDe, doc_bang  # noqa: E402


PHIEN_BAN = "TN-20261009-1"   # 09/10: chỉ siết kiểm tra đầu vào; cách tính chỉ số giữ nguyên
THU_MUC = Path(__file__).resolve().parent
FILE_MAC_DINH = THU_MUC.parent / "bo_de_tu_nhien" / "bo_de_tu_nhien.csv"
KHONG_CO = "KHONG_CO"
COT_BAT_BUOC = ("stt", "cau_hoi", "loai", "ma_thu_tuc_dung")
TEN_LOAI = {
    "tu_nhien": "Câu hỏi đời thường",
    "dong_nghia": "Dùng từ đồng nghĩa/thuật ngữ cũ",
    "khong_dau": "Gõ không dấu",
    "ngoai_pham_vi": "Ngoài phạm vi (phải từ chối)",
}
MA_THU_TUC = re.compile(r"^\d\.\d{6}$")


def ma_bo_de(text):
    """SHA256 của NỘI DUNG bộ đề sau khi bỏ BOM và chuẩn hóa xuống dòng.

    Mở rồi lưu lại bằng Excel có thể đổi BOM/xuống dòng mà không đổi nội
    dung; SHA này vẫn giữ nguyên trong trường hợp đó.
    """
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def ma_file(path):
    source = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def ma_json(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def goi_y_ma(token, ma_trong_kho):
    """Đoán mã gốc khi Excel làm hỏng mã (bỏ số 0 cuối, đổi dấu chấm)."""
    t = token.replace(",", ".").strip()
    ung_vien = set()
    m = re.fullmatch(r"(\d)\.(\d{1,6})", t)
    if m:
        ung_vien.add(f"{m.group(1)}.{m.group(2).ljust(6, '0')}")
    m = re.fullmatch(r"(\d)(\d{1,6})", t)
    if m:
        ung_vien.add(f"{m.group(1)}.{m.group(2).ljust(6, '0')}")
    return sorted(u for u in ung_vien if u in ma_trong_kho and u != token)


def doc_bo_de(path, ma_trong_kho):
    """Đọc và KIỂM TRA toàn bộ bộ đề. Lỗi bất kỳ -> LoiBoDe.

    Cấu trúc bảng (cột trùng/rỗng, thừa/thiếu ô, nháy sai) do bo_doc_csv kiểm
    tra; phần dưới kiểm tra ý nghĩa của từng dòng.
    """
    ban_ghi, text = doc_bang(path, COT_BAT_BUOC)
    de, loi = [], []
    stt_da_co, cau_da_co = {}, {}
    for vt, r in ban_ghi:
        vi_tri = f"{vt} (STT {r.get('stt') or '?'})"
        cau, loai, stt = r.get("cau_hoi", ""), r.get("loai", ""), r.get("stt", "")
        if not cau:
            loi.append(f"{vi_tri}: thiếu câu hỏi.")
            continue
        if loai not in TEN_LOAI:
            loi.append(f"{vi_tri}: loại '{loai}' không hợp lệ; chỉ dùng {', '.join(TEN_LOAI)}.")
        if not stt:
            loi.append(f"{vi_tri}: thiếu STT.")
        elif stt in stt_da_co:
            loi.append(f"{vi_tri}: STT trùng với {stt_da_co[stt]}.")
        else:
            stt_da_co[stt] = vt
        khoa = unicodedata.normalize("NFC", cau).lower()
        if khoa in cau_da_co:
            loi.append(f"{vi_tri}: câu hỏi trùng với {cau_da_co[khoa]}.")
        else:
            cau_da_co[khoa] = vt

        tokens = [t for t in re.split(r"[;\s]+", r.get("ma_thu_tuc_dung", "")) if t]
        if KHONG_CO in tokens and len(tokens) > 1:
            loi.append(f"{vi_tri}: nhãn mâu thuẫn — KHONG_CO đi cùng mã thủ tục.")
        if loai == "ngoai_pham_vi" and tokens != [KHONG_CO]:
            # Kể cả khi để trống: câu ngoài phạm vi để trống nhãn sẽ bị coi là
            # "chưa gán" và lặng lẽ rơi khỏi phép đo từ chối.
            loi.append(f"{vi_tri}: câu ngoài phạm vi phải có nhãn đúng một giá trị KHONG_CO.")
        ma = []
        for t in tokens:
            if t == KHONG_CO:
                continue
            if t in ma_trong_kho:
                ma.append(t)
                continue
            gy = goi_y_ma(t, ma_trong_kho)
            if gy:
                loi.append(f"{vi_tri}: mã '{t}' không có trong kho; có phải {' hoặc '.join(gy)}? "
                           "(Excel có thể đã bỏ số 0 cuối hoặc đổi dấu chấm — định dạng cột là Text.)")
            elif not MA_THU_TUC.match(t):
                loi.append(f"{vi_tri}: '{t}' không đúng dạng mã thủ tục (ví dụ 1.001471).")
            else:
                loi.append(f"{vi_tri}: mã '{t}' không có trong kho đang đo.")
        de.append({"stt": stt, "cau_hoi": cau, "loai": loai, "ma": sorted(set(ma)),
                   "khong_co": tokens == [KHONG_CO]})
    if not de and not loi:
        loi.append("Bộ đề không có câu hỏi nào (chỉ có dòng tiêu đề).")
    if loi:
        raise LoiBoDe(loi)
    return de, text


def ti_le(so, tong):
    return f"{so/tong*100:5.1f}% ({so}/{tong})" if tong else "không có câu"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=FILE_MAC_DINH, help="Đường dẫn CSV bộ đề")
    parser.add_argument("--luu", type=Path, help="Ghi báo cáo UTF-8 (đuôi .txt)")
    args = parser.parse_args()
    if args.luu and args.luu.suffix.lower() != ".txt":
        parser.error("File báo cáo phải có đuôi .txt để tránh ghi đè mã nguồn.")
    if not args.file.exists():
        parser.error(f"Không thấy file bộ đề: {args.file}")

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
        try:
            de, text = doc_bo_de(args.file, {d.procedure_code for d in docs if d.procedure_code})
        except LoiBoDe as exc:
            print("BỘ ĐỀ CÓ LỖI — chưa tính chỉ số. Sửa các lỗi dưới đây rồi chạy lại:")
            for l in exc.loi:
                print("  - " + l)
            return 2

        ra("=" * 76)
        ra("ĐÁNH GIÁ TRA CỨU — CÂU HỎI TỰ NHIÊN CÓ GÁN NHÃN")
        ra("=" * 76)
        ra(f"Phiên bản bộ đo : {PHIEN_BAN}")
        ra(f"Kho dữ liệu     : {len(docs):,} thủ tục".replace(",", "."))
        ra(f"SHA256 bộ đo    : {ma_file(__file__)}")
        ra(f"SHA256 search.py: {ma_file(search_module.__file__)}")
        ra(f"SHA256 bộ đề    : {ma_bo_de(text)}  (nội dung, bỏ BOM, chuẩn hóa xuống dòng)")
        ra("SHA256 kho tra cứu: " + ma_json([
            [d.id, d.procedure_code, d.title, d.category, d.status] for d in docs]))
        ra("Chỉ so sánh trước/sau khi bộ đề và kho giống nhau (cùng SHA256).")
        ra()

        print("Đang xây chỉ mục...", flush=True)
        search_module.xay_chi_muc(docs)
        chi_tiet = []
        for c in de:
            kq = search_module.search(c["cau_hoi"], docs)
            dung = set(c["ma"])
            vt = next((i for i, (d, _, _) in enumerate(kq, 1) if d.procedure_code in dung), None)
            chi_tiet.append((c, kq, vt))

        co_ma = [x for x in chi_tiet if x[0]["ma"]]
        khong_co = [x for x in chi_tiet if x[0]["khong_co"]]
        chua = len(chi_tiet) - len(co_ma) - len(khong_co)
        tong = len(chi_tiet)
        rong = sum(1 for _, kq, _ in chi_tiet if not kq)

        ra("-" * 76)
        ra(f"TỔNG QUAN: {tong} câu; có mã đúng {len(co_ma)}; KHONG_CO {len(khong_co)}; chưa gán {chua}")
        ra(f"Trả về rỗng trên toàn bộ (không cần nhãn): {ti_le(rong, tong)}")
        ra()

        def trong_pham_vi(nhom, tieu_de):
            n = len(nhom)
            ra(f"{tieu_de} ({n} câu)")
            if not n:
                ra("  không có câu")
                return
            t1 = sum(1 for _, _, vt in nhom if vt == 1)
            t5 = sum(1 for _, _, vt in nhom if vt and vt <= 5)
            ra(f"  Top-1        : {ti_le(t1, n)}")
            ra(f"  Top-5        : {ti_le(t5, n)}")
            ra(f"  MRR          : {sum(1/vt for _, _, vt in nhom if vt)/n:.6f}")
            ra(f"  Trả về rỗng  : {ti_le(sum(1 for _, kq, _ in nhom if not kq), n)}")
            ra(f"  Lạc đề       : {ti_le(sum(1 for _, kq, vt in nhom if kq and not vt), n)}"
               "  — có kết quả nhưng không có mã đúng")
            ra(f"  Số kết quả TB: {sum(len(kq) for _, kq, _ in nhom)/n:.2f}")

        ra("-" * 76)
        trong_pham_vi(co_ma, "A. TRONG PHẠM VI — câu có mã đúng")
        theo_loai = defaultdict(list)
        for x in co_ma:
            theo_loai[x[0]["loai"]].append(x)
        for loai in sorted(theo_loai):
            ra()
            trong_pham_vi(theo_loai[loai], f"   Theo loại: {TEN_LOAI.get(loai, loai)}")
        ra()

        ra("-" * 76)
        n = len(khong_co)
        ra(f"B. NGOÀI PHẠM VI — câu KHONG_CO, kết quả mong muốn là rỗng ({n} câu)")
        if n:
            sai = [(c, kq) for c, kq, _ in khong_co if kq]
            ra(f"  Từ chối đúng : {ti_le(n - len(sai), n)}")
            ra(f"  Trả lời sai  : {ti_le(len(sai), n)}")
            if sai:
                cao = sorted((kq[0][2] for _, kq in sai), reverse=True)
                ra(f"  Phần trăm cao nhất hiển thị trên câu trả lời sai: {cao[0]}%; "
                   f"trung vị {cao[len(cao)//2]}%")
        else:
            ra("  không có câu")
        ra()

        if not co_ma and not khong_co:
            ra("Chưa có câu nào được gán nhãn nên chưa tính chỉ số A, B.")
            ra("Điền cột ma_thu_tuc_dung theo bo_de_tu_nhien/HUONG_DAN_GAN_NHAN.md.")
            ra()

        ra("-" * 76)
        ra("CHI TIẾT TỪNG CÂU")
        ra("-" * 76)
        for c, kq, vt in chi_tiet:
            if c["ma"]:
                tt = f"hạng đúng: {vt}" if vt else "KHÔNG có mã đúng trong kết quả"
            elif c["khong_co"]:
                tt = "từ chối đúng" if not kq else "SAI — lẽ ra phải rỗng"
            else:
                tt = "chưa gán nhãn"
            ra(f"Câu {c['stt']} [{c['loai']}] {c['cau_hoi']}")
            ra(f"  {len(kq)} kết quả; {tt}")
            for d, _, pt in kq[:3]:
                dau = " ✓" if d.procedure_code in set(c["ma"]) else ""
                ra(f"    {pt:3d}%  {d.procedure_code} | {d.title[:88]}{dau}")
            ra()
    finally:
        db.close()

    if args.luu:
        args.luu.write_text("\n".join(dong) + "\n", encoding="utf-8")
        print(f"Đã ghi báo cáo vào: {args.luu.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
