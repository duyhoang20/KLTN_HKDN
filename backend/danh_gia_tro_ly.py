"""Đánh giá TRỢ LÝ hỏi–đáp, phiên bản TL-20261014-1 (14/10: báo thêm dòng sai lệch số–đơn vị theo bộ đối chiếu bản chặt).

Đo riêng từng khâu, không gộp thành một con số:

  1. QUYẾT ĐỊNH — câu trong phạm vi có được trả lời không; câu ngoài phạm vi có
     bị trả lời không.
  2. ĐÚNG THỦ TỤC — trong các lần trả lời thẳng, bao nhiêu lần chọn đúng thủ
     tục. Có dẫn nguồn KHÔNG có nghĩa là đúng thủ tục: hai việc đo riêng.
  3. ĐÚNG Ý ĐỊNH — nhận ra người dân hỏi hồ sơ, lệ phí, thời hạn, nơi nộp...
  4. ĐỐI CHIẾU NGUỒN ĐỘC LẬP — với câu trả lời đúng thủ tục, so các dòng trả lời
     với JSON gốc bằng doi_chieu_nguon.py (không dùng hàm trích của trợ lý):
       - độ bao phủ: dữ kiện của nguồn có mặt đủ trong câu trả lời không;
       - căn cứ: mỗi dòng trả lời có chứa chuỗi có thật trong nguồn không.
  5. LỜI DẪN CỦA MÔ HÌNH NGÔN NGỮ (khi chạy --mo-hinh): bao nhiêu lời dẫn bị
     loại vì chứa dữ kiện, và lý do.
  6. THỜI GIAN phản hồi.

Chế độ --toan-kho: bỏ qua bộ câu hỏi, chạy đối chiếu nguồn cho MỌI thủ tục có
dữ liệu chi tiết trong kho và MỌI mục (hồ sơ, phí, thời hạn...). Đây là phép
kiểm tra phạm vi rộng nhất cho tầng trích dữ liệu.

Bộ đề: ../bo_de_tu_nhien/bo_de_tro_ly.csv — cột stt, cau_hoi, y_dinh_dung,
ma_thu_tuc_dung (nhiều mã cách nhau bằng dấu chấm phẩy; KHONG_CO = ngoài phạm
vi), ghi_chu. Bộ này TRÙNG một phần câu với bộ phát triển và bộ kiểm tra của
danh_gia_tu_nhien.py nên KHÔNG phải bộ kiểm tra độc lập.

Chạy từ thư mục backend (đã kích hoạt venv):
    python danh_gia_tro_ly.py --luu bao_cao_tro_ly.txt
    python danh_gia_tro_ly.py --toan-kho --luu bao_cao_doi_chieu_toan_kho.txt
    python danh_gia_tro_ly.py --mo-hinh --luu bao_cao_tro_ly_llm.txt
"""
import argparse
import hashlib
import re
import statistics
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
sys.path.insert(0, str(THU_MUC))
from bo_doc_csv import LoiBoDe, doc_bang  # noqa: E402

PHIEN_BAN = "TL-20261014-1"   # 14/10: thêm số dòng sai lệch của bộ đối chiếu bản chặt DC-20261014-2
FILE_MAC_DINH = THU_MUC.parent / "bo_de_tu_nhien" / "bo_de_tro_ly.csv"
KHONG_CO = "KHONG_CO"
COT = ("stt", "cau_hoi", "y_dinh_dung", "ma_thu_tuc_dung")
MA_THU_TUC = re.compile(r"^\d\.\d{6}$")


def pt(a, b):
    return f"{100 * a / b:5.1f}% ({a}/{b})" if b else "không có câu"


def doc_bo_de(path, ma_kho, y_dinh_hop_le):
    """Đọc bộ đề trợ lý: cấu trúc do bo_doc_csv kiểm tra, ở đây kiểm tra ý nghĩa."""
    ban_ghi, text = doc_bang(path, COT)
    de, loi, stt_co, cau_co = [], [], {}, {}
    for vt, r in ban_ghi:
        v = f"{vt} (STT {r['stt'] or '?'})"
        if not r["cau_hoi"]:
            loi.append(f"{v}: thiếu câu hỏi.")
            continue
        if not r["stt"]:
            loi.append(f"{v}: thiếu STT.")
        elif r["stt"] in stt_co:
            loi.append(f"{v}: STT trùng với {stt_co[r['stt']]}.")
        else:
            stt_co[r["stt"]] = vt
        k = unicodedata.normalize("NFC", r["cau_hoi"]).lower()
        if k in cau_co:
            loi.append(f"{v}: câu hỏi trùng với {cau_co[k]}.")
        else:
            cau_co[k] = vt
        tokens = [t for t in re.split(r"[;\s]+", r["ma_thu_tuc_dung"]) if t]
        if not tokens:
            loi.append(f"{v}: chưa gán nhãn. Bộ đề trợ lý yêu cầu mọi câu có mã thủ tục hoặc KHONG_CO.")
        if KHONG_CO in tokens and len(tokens) > 1:
            loi.append(f"{v}: KHONG_CO đi cùng mã thủ tục.")
        for t in tokens:
            if t != KHONG_CO and not MA_THU_TUC.match(t):
                loi.append(f"{v}: '{t}' không đúng dạng mã thủ tục (ví dụ 1.001471).")
            elif t != KHONG_CO and t not in ma_kho:
                loi.append(f"{v}: mã {t} không có trong kho đang đo.")
        y = r["y_dinh_dung"]
        if y and y not in y_dinh_hop_le:
            loi.append(f"{v}: ý định '{y}' không hợp lệ; chỉ dùng {', '.join(y_dinh_hop_le)}.")
        if tokens == [KHONG_CO] and y:
            loi.append(f"{v}: câu ngoài phạm vi (KHONG_CO) không được có ý định.")
        de.append(dict(r, ma={t for t in tokens if t != KHONG_CO}, ngoai=tokens == [KHONG_CO]))
    if not de and not loi:
        loi.append("Bộ đề không có câu hỏi nào (chỉ có dòng tiêu đề).")
    if loi:
        raise LoiBoDe(loi)
    return de, text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", type=Path, default=FILE_MAC_DINH)
    ap.add_argument("--luu", type=Path)
    ap.add_argument("--mo-hinh", action="store_true", help="Gọi cả lớp mô hình ngôn ngữ (nếu đã cấu hình trong .env)")
    ap.add_argument("--toan-kho", action="store_true", help="Đối chiếu nguồn cho mọi thủ tục có dữ liệu chi tiết")
    ap.add_argument("--json", type=Path, help="Dùng với --toan-kho: đọc thủ tục từ file JSON (danh sách "
                    "{procedure_code, data}) thay vì từ database, ví dụ ../bao_cao/mau_21_thu_tuc_du_lieu_chi_tiet.json")
    a = ap.parse_args()

    from app.database import SessionLocal
    from app import models, search as S, tro_ly
    from app import mo_hinh_ngon_ngu as llm
    from app.hieu_truy_van import Y_DINH_TEN
    import doi_chieu_nguon as DC

    db = SessionLocal()
    docs = (db.query(models.GuidanceDocument).filter(models.GuidanceDocument.status == "published")
            .order_by(models.GuidanceDocument.id).all())
    dong = []

    def ra(s=""):
        dong.append(s)
        print(s)

    def luu():
        db.close()
        if a.luu:
            a.luu.write_text("\n".join(dong) + "\n", encoding="utf-8")
            print(f"\nĐã ghi báo cáo vào: {a.luu}")

    ra("=" * 76)
    ra("ĐÁNH GIÁ TRỢ LÝ HỎI–ĐÁP" + (" — ĐỐI CHIẾU NGUỒN TOÀN KHO" if a.toan_kho else ""))
    ra("=" * 76)
    ra(f"Phiên bản bộ đo : {PHIEN_BAN}")
    ra(f"Kho đang đo     : {len(docs):,} bản ghi công khai".replace(",", "."))

    # ------------------------------------------------------------------ toàn kho
    if a.toan_kho:
        if a.json:
            import json
            from types import SimpleNamespace
            co_data = [SimpleNamespace(**x) for x in json.loads(a.json.read_text(encoding="utf-8"))]
            ra(f"Nguồn bản ghi   : file {a.json.name} (không đọc database)")
        else:
            co_data = [d for d in docs if d.data and (d.data or {}).get("NguonDuLieu") != "CAN_BO_BIEN_TAP"]
        ra(f"Thủ tục có dữ liệu chi tiết: {len(co_data):,}".replace(",", "."))
        ra("Mỗi thủ tục × 9 mục (hồ sơ, trình tự, nơi nộp, thời hạn, lệ phí, điều kiện, kết quả,")
        ra("căn cứ pháp lý, đối tượng). Nguồn đối chiếu đọc thẳng JSON gốc, không qua hàm trích của trợ lý.")
        ra()
        tong = Counter()
        mau_thieu, mau_kcc, mau_sl = [], [], []
        for d in co_data:
            for y in tro_ly.DUNG_MUC:
                m = tro_ly.trich_muc(d.data, [y])[0]
                r = DC.doi_chieu(d.data, y, m["dong"])
                tong[y + "_dk"] += r["so_du_kien"]
                tong[y + "_co"] += r["co_trong_tra_loi"]
                tong[y + "_dong"] += r["so_dong"]
                tong[y + "_kcc"] += len(r["dong_khong_can_cu"])
                tong[y + "_sl"] += len(r.get("dong_sai_lech", []))
                tong[y + "_tt_thieu"] += 1 if r["thieu"] else 0
                if r["thieu"] and len(mau_thieu) < 20:
                    mau_thieu.append(f"{d.procedure_code} [{y}] thiếu: {'; '.join(r['thieu'][:3])}")
                if r["dong_khong_can_cu"] and len(mau_kcc) < 20:
                    mau_kcc.append(f"{d.procedure_code} [{y}] dòng không căn cứ: {r['dong_khong_can_cu'][0][:100]}")
                if r.get("dong_sai_lech") and len(mau_sl) < 20:
                    mau_sl.append(f"{d.procedure_code} [{y}] {r['dong_sai_lech'][0][:150]}")
        ra(f"Bộ đối chiếu    : {DC.PHIEN_BAN}")
        ra(f"{'Mục':<12}{'Dữ kiện có trong trả lời':>30}{'Thủ tục thiếu dữ kiện':>24}{'Dòng không căn cứ':>22}{'Dòng sai lệch':>16}")
        for y in tro_ly.DUNG_MUC:
            ra(f"{y:<12}{tong[y + '_co']:>16} / {tong[y + '_dk']:<11}{tong[y + '_tt_thieu']:>24}"
               f"{tong[y + '_kcc']:>14} / {tong[y + '_dong']:<6}{tong[y + '_sl']:>10}")
        tdk = sum(tong[y + "_dk"] for y in tro_ly.DUNG_MUC)
        tco = sum(tong[y + "_co"] for y in tro_ly.DUNG_MUC)
        tdo = sum(tong[y + "_dong"] for y in tro_ly.DUNG_MUC)
        tkc = sum(tong[y + "_kcc"] for y in tro_ly.DUNG_MUC)
        ra()
        tsl = sum(tong[y + "_sl"] for y in tro_ly.DUNG_MUC)
        ra(f"TỔNG: độ bao phủ {pt(tco, tdk)}; dòng không có căn cứ {tkc}/{tdo}; "
           f"dòng sai lệch (cặp số–đơn vị không có trong nguồn hoặc của chủ thể khác) {tsl}/{tdo}")
        # Bổ sung 16/10: câu trả lời TỔNG HỢP (phần lời đáp đặt trên bảng chi tiết) cũng phải
        # không có cặp số–đơn vị sai nguồn hoặc gắn nhầm chủ thể.
        # Bổ sung 20/10 bản 3 (báo cáo kiểm thử độc lập F06): đếm thêm ĐỘ ĐẦY ĐỦ của phần tổng hợp
        # với những thứ phép đếm số–đơn vị không thấy: tên trường hợp (điều kiện), tên giấy tờ,
        # cách tính phí, và lỗi báo “nguồn không ghi phí” khi nguồn có dữ liệu phí.
        tt_dong = tt_sl = 0
        mau_tt = []
        du = Counter()
        mau_thieu_tt = []

        def co(chuoi, van_ban):
            return " ".join(str(chuoi).split()).lower() in " ".join(van_ban.split()).lower()

        def chu_tt(tt):
            return " ".join([k.get("text", "") for k in tt["khoi"]] + [i for k in tt["khoi"] for i in k.get("items", [])])
        for d in co_data:
            for y in tro_ly.TOM_TAT:
                tt = tro_ly.tong_hop(d, [y])
                dong_tt = [k["text"] for k in tt["khoi"] if k["loai"] == "p" and not k["text"].startswith("Dữ liệu nguồn không ghi")]
                dong_tt += [i for k in tt["khoi"] if k["loai"] == "ds" for i in k["items"]]
                r = DC.doi_chieu(d.data, y, dong_tt)
                tt_dong += len(dong_tt)
                tt_sl += len(r["dong_sai_lech"])
                if r["dong_sai_lech"] and len(mau_tt) < 20:
                    mau_tt.append(f"{d.procedure_code} [{y}] {r['dong_sai_lech'][0][:150]}")
                van = chu_tt(tt)
                data = d.data or {}
                kiem = []
                if y == "ho_so":
                    for h in tro_ly._ds(data.get("ThanhPhanHoSo")):
                        if isinstance(h, dict):
                            if tro_ly._txt(h.get("TenTruongHop")) and any(
                                    isinstance(g, dict) and tro_ly._txt(g.get("TenGiayTo")) for g in tro_ly._ds(h.get("DanhSachGiayTo"))):
                                kiem.append(("ten_truong_hop", tro_ly._txt(h.get("TenTruongHop"))))
                            for g in tro_ly._ds(h.get("DanhSachGiayTo")):
                                if isinstance(g, dict) and tro_ly._txt(g.get("TenGiayTo")):
                                    kiem.append(("ten_giay_to", tro_ly._txt(g.get("TenGiayTo"))))
                if y == "le_phi":
                    phi = [p for p in tro_ly._ds(data.get("DanhSachPhi"))] + [
                        p for c in tro_ly._ds(data.get("CachThucThucHien")) if isinstance(c, dict) for p in tro_ly._ds(c.get("DanhSachPhi"))]
                    for p in phi:
                        if isinstance(p, dict) and tro_ly._txt(p.get("CachTinhPhi")):
                            kiem.append(("cach_tinh_phi", tro_ly._txt(p.get("CachTinhPhi"))))
                    if any(isinstance(p, dict) and any(tro_ly._txt(p.get(k)) for k in ("TenPhi", "SoTien", "CachTinhPhi", "ThoiDiemThu")) for p in phi):
                        du["co_phi"] += 1
                        if "không ghi phí" in van:
                            du["bao_nham_khong_phi"] += 1
                            mau_thieu_tt.append(f"{d.procedure_code} [le_phi] báo nguồn không ghi phí dù nguồn có dữ liệu phí")
                for loai, gt in kiem:
                    du[loai + "_tong"] += 1
                    if co(gt, van):
                        du[loai + "_co"] += 1
                    elif len(mau_thieu_tt) < 20:
                        mau_thieu_tt.append(f"{d.procedure_code} [{y}] thiếu {loai}: {gt[:100]}")
        ra(f"CÂU TRẢ LỜI TỔNG HỢP: dòng sai lệch (sai cặp số–đơn vị hoặc gắn nhầm chủ thể) {tt_sl}/{tt_dong}")
        ra(f"  Độ đầy đủ: tên trường hợp {du['ten_truong_hop_co']}/{du['ten_truong_hop_tong']}; "
           f"tên giấy tờ {du['ten_giay_to_co']}/{du['ten_giay_to_tong']}; "
           f"cách tính phí {du['cach_tinh_phi_co']}/{du['cach_tinh_phi_tong']}; "
           f"báo nhầm “nguồn không ghi phí” {du['bao_nham_khong_phi']}/{du['co_phi']} thủ tục có dữ liệu phí")
        ra("  Chưa đo: đánh giá ngữ nghĩa bằng người (đúng ý, đủ điều kiện ngoài các trường trên).")
        for x in mau_thieu_tt:
            ra("  " + x)
        for x in mau_tt:
            ra("  " + x)
        if mau_thieu:
            ra("\nVí dụ dữ kiện bị thiếu (tối đa 20):")
            for x in mau_thieu:
                ra("  " + x)
        if mau_kcc:
            ra("\nVí dụ dòng không có căn cứ (tối đa 20):")
            for x in mau_kcc:
                ra("  " + x)
        if mau_sl:
            ra("\nVí dụ dòng sai lệch số–đơn vị (tối đa 20):")
            for x in mau_sl:
                ra("  " + x)
        ra("\nGiới hạn: so khớp theo chuỗi; bắt được bỏ sót, cắt bớt, tách phí khỏi thời hạn, sai đơn vị")
        ra("thời gian/tiền và sai số bản (kiểm chứng bằng kiem_tra_bo_doi_chieu.py). Không bắt được khẳng")
        ra("định không có chữ số (ví dụ “miễn lệ phí”) nếu nó không làm mất dữ kiện; không đánh giá văn phong.")
        luu()
        return

    # ------------------------------------------------------------------ theo bộ đề
    S.xay_chi_muc(docs)
    try:
        de, text = doc_bo_de(a.file, {d.procedure_code for d in docs if d.procedure_code}, list(Y_DINH_TEN))
    except LoiBoDe as e:
        print("BỘ ĐỀ CÓ LỖI — chưa tạo báo cáo. Sửa các lỗi sau rồi chạy lại:")
        for x in e.loi:
            print("  - " + x)
        sys.exit(2)
    trong = [r for r in de if not r["ngoai"]]
    ngoai = [r for r in de if r["ngoai"]]
    dung_llm = a.mo_hinh and llm.da_bat()
    ra(f"SHA256 bộ đề    : {hashlib.sha256(text.replace(chr(13) + chr(10), chr(10)).encode('utf-8')).hexdigest()}")
    ra(f"Ngưỡng trả lời  : {tro_ly.NGUONG_TRA_LOI}%")
    ra(f"Mô hình ngôn ngữ: {llm.ten_mo_hinh() + ' (chỉ viết lời dẫn)' if dung_llm else 'KHÔNG dùng'}")
    ra(f"Bộ đề           : {len(de)} câu = {len(trong)} trong phạm vi + {len(ngoai)} ngoài phạm vi")
    ra("Lưu ý: bộ đề này trùng một phần câu với bộ phát triển/kiểm tra của danh_gia_tu_nhien.py.")
    ra()

    kq = []
    for r in de:
        t0 = time.perf_counter()
        d = tro_ly.tra_loi(r["cau_hoi"], docs, dung_mo_hinh=dung_llm)
        kq.append((r, d, (time.perf_counter() - t0) * 1000))

    def dung(r, ma):
        return ma in r["ma"]

    tl = [(r, d) for r, d, _ in kq if not r["ngoai"] and d["trang_thai"] == "tra_loi"]
    hoi_lai = [(r, d) for r, d, _ in kq if not r["ngoai"] and d["trang_thai"] == "can_lam_ro"]
    tu_choi_nham = [r for r, d, _ in kq if not r["ngoai"] and d["trang_thai"] == "ngoai_pham_vi"]
    tl_dung = [(r, d) for r, d in tl if dung(r, d["thu_tuc"]["ma_thu_tuc"])]
    tl_sai = [(r, d) for r, d in tl if not dung(r, d["thu_tuc"]["ma_thu_tuc"])]
    tl_sai_co_goi_y = [(r, d) for r, d in tl_sai if any(dung(r, c["ma_thu_tuc"]) for c in d["lua_chon"])]
    hoi_lai_co = [(r, d) for r, d in hoi_lai if any(dung(r, c["ma_thu_tuc"]) for c in d["lua_chon"])]
    ng = Counter(d["trang_thai"] for r, d, _ in kq if r["ngoai"])
    co_y = [(r, d) for r, d, _ in kq if r["y_dinh_dung"]]
    y_dung = [1 for r, d in co_y if r["y_dinh_dung"] in [y["ma"] for y in d["hieu"]["y_dinh"]]]

    ra("-" * 76)
    ra("1. QUYẾT ĐỊNH")
    ra("-" * 76)
    ra(f"  Trong phạm vi ({len(trong)}): trả lời thẳng {pt(len(tl), len(trong))}; hỏi lại {pt(len(hoi_lai), len(trong))}; "
       f"từ chối nhầm {pt(len(tu_choi_nham), len(trong))}")
    ra(f"  Ngoài phạm vi ({len(ngoai)}): từ chối {pt(ng['ngoai_pham_vi'], len(ngoai))}; "
       f"hỏi lại {pt(ng['can_lam_ro'], len(ngoai))}; TRẢ LỜI SAI {pt(ng['tra_loi'], len(ngoai))}")
    ra()
    ra("-" * 76)
    ra("2. ĐÚNG THỦ TỤC (dẫn nguồn đúng tên/mã KHÔNG đồng nghĩa với chọn đúng thủ tục)")
    ra("-" * 76)
    ra(f"  Trả lời thẳng đúng thủ tục (câu trong phạm vi): {pt(len(tl_dung), len(tl))}")
    ra(f"  Trả lời thẳng đúng thủ tục (tính cả câu ngoài phạm vi bị trả lời): {pt(len(tl_dung), len(tl) + ng['tra_loi'])}")
    ra(f"  Trả lời SAI thủ tục, nhưng thủ tục đúng có trong “thủ tục tương tự”: {pt(len(tl_sai_co_goi_y), len(tl_sai))}")
    ra(f"  Hỏi lại, thủ tục đúng có trong các lựa chọn: {pt(len(hoi_lai_co), len(hoi_lai))}")
    ra()
    ra("-" * 76)
    ra("3. ĐÚNG Ý ĐỊNH")
    ra("-" * 76)
    ra(f"  {pt(len(y_dung), len(co_y))}  (câu hỏi dùng cách hỏi có trong bảng từ đệm; cách hỏi lạ chưa được đo)")
    ra()
    ra("-" * 76)
    ra("4. ĐỐI CHIẾU NGUỒN ĐỘC LẬP (câu trả lời đúng thủ tục)")
    ra("-" * 76)
    khong_data = sum(1 for r, d in tl_dung if not d["muc"])
    dk = co = so_dong = kcc = sl = 0
    for r, d in tl_dung:
        doc = next((x for x in docs if x.id == d["thu_tuc"]["id"]), None)
        for m in d["muc"]:
            x = DC.doi_chieu(doc.data, m["ma"], m["dong"])
            dk, co = dk + x["so_du_kien"], co + x["co_trong_tra_loi"]
            so_dong, kcc = so_dong + x["so_dong"], kcc + len(x["dong_khong_can_cu"])
            sl += len(x.get("dong_sai_lech", []))
    ra(f"  Câu trả lời đúng thủ tục nhưng bản ghi chưa có dữ liệu chi tiết: {khong_data}/{len(tl_dung)}")
    ra(f"  Độ bao phủ dữ kiện nguồn: {pt(co, dk)}")
    ra(f"  Dòng trả lời không có căn cứ trong nguồn: {kcc}/{so_dong}")
    ra(f"  Dòng sai lệch: cặp số–đơn vị không có trong nguồn hoặc của chủ thể khác ({DC.PHIEN_BAN}): {sl}/{so_dong}")
    ra("  (Phạm vi rộng hơn: chạy thêm --toan-kho.)")
    if dung_llm:
        kc = [d["kiem_chung"] for _, d, _ in kq if d.get("kiem_chung")]
        dat = sum(1 for k in kc if k.get("dat"))
        ly_do = Counter(x.split(":")[0] for k in kc for x in k.get("ly_do", []))
        ra()
        ra("-" * 76)
        ra("5. LỜI DẪN CỦA MÔ HÌNH NGÔN NGỮ")
        ra("-" * 76)
        ra(f"  Lời dẫn được dùng: {pt(dat, len(kc))}; bị loại vì: {dict(ly_do) or 'không có'}")
        ra("  Dữ kiện trong câu trả lời luôn do hệ thống trích từ nguồn, không do mô hình viết.")
    tg = sorted(t for _, _, t in kq)
    ra()
    ra("-" * 76)
    ra("6. THỜI GIAN (ms, gọi hàm trực tiếp, không tính mạng)")
    ra("-" * 76)
    ra(f"  trung vị {statistics.median(tg):.1f} · P95 {tg[min(len(tg) - 1, int(len(tg) * 0.95))]:.1f} · lớn nhất {tg[-1]:.1f}")
    ra()
    ra("-" * 76)
    ra("CHI TIẾT TỪNG CÂU")
    ra("-" * 76)
    for r, d, t in kq:
        tt = d["trang_thai"]
        ra(f"Câu {r['stt']}: {r['cau_hoi']}")
        yd = ",".join(y["ma"] for y in d["hieu"]["y_dinh"]) or "-"
        if tt == "tra_loi":
            ok = "ĐÚNG" if dung(r, d["thu_tuc"]["ma_thu_tuc"]) else "SAI"
            ra(f"  -> TRẢ LỜI [{ok}] {d['thu_tuc']['ma_thu_tuc']} ({d['thu_tuc']['do_khop']}%) {d['thu_tuc']['ten'][:70]}")
        elif tt == "can_lam_ro":
            ra(f"  -> HỎI LẠI, {len(d['lua_chon'])} lựa chọn, cao nhất {d['lua_chon'][0]['do_khop']}%")
        else:
            ra("  -> TỪ CHỐI")
        ra(f"     ý định nhận được: {yd} | mong muốn: {r['y_dinh_dung'] or '-'} | {t:.0f} ms")
    luu()


if __name__ == "__main__":
    main()
