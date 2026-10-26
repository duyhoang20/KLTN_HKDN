"""
Trợ lý hỏi–đáp thủ tục hành chính theo mô hình RAG (truy xuất rồi mới trả lời).

LUỒNG XỬ LÝ
    câu hỏi
      │  1. HIỂU CÂU HỎI  (hieu_truy_van.py): bỏ từ đệm, nhận ý định hỏi
      │     (hồ sơ / lệ phí / thời hạn / nơi nộp / trình tự...), thay từ đồng nghĩa
      ▼
    2. TRUY XUẤT  (search.py, BM25): xếp hạng thủ tục theo câu hỏi
      ▼
    3. QUYẾT ĐỊNH
         - không có kết quả                -> TỪ CHỐI (ngoài phạm vi)
         - có kết quả nhưng độ khớp thấp   -> HỎI LẠI, đưa vài thủ tục để chọn
         - độ khớp cao                     -> TRẢ LỜI
      ▼
    4. TRÍCH MỤC: lấy đúng các mục dữ liệu ứng với ý định từ bản ghi thủ tục
       (ví dụ hỏi "cần giấy tờ gì" -> mục ThanhPhanHoSo)
      ▼
    5. SINH CÂU TRẢ LỜI
         - DỮ KIỆN (giấy tờ, thời hạn, lệ phí, điều kiện, địa chỉ...) LUÔN được
           dựng trực tiếp từ dữ liệu có cấu trúc, liệt kê đủ từng dòng.
         - Lời dẫn mặc định dựng bằng khuôn mẫu. Tùy chọn (sửa 09/10/2026):
           mô hình ngôn ngữ CHỈ viết lời dẫn 1–3 câu và bị CẤM nêu dữ kiện.
           Lời dẫn có chữ số, số đếm bằng chữ, đơn vị tiền/thời gian hay các
           khẳng định kiểu "miễn phí", "không cần" bị loại, quay về khuôn mẫu.
           Lý do: kiểm tra "con số có trong nguồn" không bắt được lỗi đổi đơn
           vị, tráo số giữa hai trường hay khẳng định sai không có chữ số.
      ▼
    câu trả lời + NGUỒN (mã thủ tục, tên, mục dữ liệu)

NGUYÊN TẮC
    - Kho dữ liệu là nguồn sự thật duy nhất; mô hình ngôn ngữ không được thêm
      thủ tục, thời hạn, mức phí hay giấy tờ.
    - Không gộp nhiều thời hạn/nhiều mức phí thành một con số: liệt kê đủ.
    - Mục nào dữ liệu nguồn để trống thì nói rõ là nguồn không ghi.
    - Luôn kèm nguồn; thà hỏi lại hoặc từ chối còn hơn trả lời sai thủ tục.
"""
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Iterable

from . import search as search_module
from .hieu_truy_van import Y_DINH_TEN, phan_tich
from . import mo_hinh_ngon_ngu as llm
from . import giao_tiep

# Ngưỡng quyết định của trợ lý, chọn trên bộ câu hỏi phát triển (xem báo cáo
# bao_cao/BAO_CAO_20261008.md): ở mức >= 60% hệ thống từ chối được 73/75 câu
# ngoài phạm vi mà vẫn giữ 40/50 câu trong phạm vi.
NGUONG_TRA_LOI = 60
SO_LUA_CHON = 5
SO_TUONG_TU = 4

M_NOP = {"DIRECT": "Trực tiếp", "ONLINE": "Trực tuyến", "POSTAL": "Qua bưu điện",
         "BKAV": "Dịch vụ bưu chính", "EMAIL": "Qua email", "FAX": "Qua fax"}
M_DVTG = {"WORKING_DAY": "ngày làm việc", "DAY": "ngày", "MONTH": "tháng", "HOUR": "giờ",
          "YEAR": "năm", "MINUTE": "phút", "WEEK": "tuần"}
M_TIEN = {"VND": "đồng", "USD": "USD"}
CAP_AP_DUNG = [("ApDungCapXa", "cấp xã"), ("ApDungCapTinh", "cấp tỉnh"), ("ApDungCapBo", "cấp bộ"),
               ("ApDungCoQuanKhac", "cơ quan khác"), ("ApDungCoQuanNganhDoc", "cơ quan ngành dọc")]

# ý định -> các trường dữ liệu gốc dùng để trả lời
TRUONG_THEO_Y_DINH = {
    "ho_so": ["ThanhPhanHoSo"],
    "trinh_tu": ["CacBuocThucHien"],
    "noi_nop": ["DiaChiTiepNhanHoSo", "ApDungCapXa", "ApDungCapTinh", "ApDungCapBo",
                "ApDungCoQuanKhac", "ApDungCoQuanNganhDoc", "CachThucThucHien"],
    "thoi_han": ["CachThucThucHien"],
    "le_phi": ["DanhSachPhi", "CachThucThucHien"],
    "dieu_kien": ["YeuCauDieuKien"],
    "ket_qua": ["DanhSachKetQua"],
    "can_cu": ["DanhSachCanCuPhapLy"],
    "doi_tuong": ["DoiTuongThucHien"],
}
# Khi câu hỏi không nêu ý định cụ thể: trả lời tổng quan theo thứ tự này
Y_DINH_TONG_QUAN = ["doi_tuong", "noi_nop", "ho_so", "le_phi", "ket_qua"]
M_THU = {"AT_RESULT_COLLECTION": "khi nhận kết quả", "AT_SUBMISSION": "khi nộp hồ sơ"}


def _txt(v) -> str:
    return "" if v is None else str(v).strip()


def _ds(v) -> List:
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def _thoi_han(c: Dict) -> str:
    n, dv = _txt(c.get("ThoiGianXuLy")), _txt(c.get("DonViThoiGian"))
    if not n:
        return ""
    return f"{n} {M_DVTG.get(dv, dv)}".strip()      # đơn vị lạ: giữ nguyên mã


def _tien(p: Dict) -> str:
    raw = _txt(p.get("SoTien"))
    if not raw:
        return ""
    if re.fullmatch(r"-?\d+", raw):                  # chỉ định dạng số nguyên rõ ràng
        raw = f"{int(raw):,}".replace(",", ".")
    dv = _txt(p.get("MaTienTe"))
    return f"{raw} {M_TIEN.get(dv, dv)}".strip()


def _phang(v, nhan: str = "") -> List[str]:
    """
    Trải MỌI giá trị chữ trong một cấu trúc bất kỳ (chuỗi, dict, list lồng nhau)
    thành các dòng, giữ thứ tự và tên trường gốc. Dùng cho trường mà API có thể
    trả về dạng chuỗi hoặc dạng cấu trúc (địa chỉ, điều kiện...), để trợ lý
    không bao giờ báo "nguồn không ghi" khi nguồn thực ra có ghi.
    """
    out: List[str] = []
    if isinstance(v, dict):
        for k, x in v.items():
            out.extend(_phang(x, k))
    elif isinstance(v, list):
        for x in v:
            out.extend(_phang(x, nhan))
    else:
        t = _txt(v)
        if t:
            out.append(f"{nhan}: {t}" if nhan else t)
    return out


# ------------------------- dựng từng mục trả lời -------------------------
# Mỗi hàm trả về TOÀN BỘ các dòng, không gộp dòng giống nhau, không cắt bớt.

def _muc_ho_so(d: Dict) -> List[str]:
    out = []
    cac_th = [h for h in _ds(d.get("ThanhPhanHoSo")) if isinstance(h, dict)]
    nhieu = len(cac_th) > 1
    for i, h in enumerate(cac_th, 1):
        ten = _txt(h.get("TenTruongHop"))
        giay = [g for g in _ds(h.get("DanhSachGiayTo")) if isinstance(g, dict) and _txt(g.get("TenGiayTo"))]
        if not giay:
            continue
        if nhieu or ten:
            out.append(f"Trường hợp {i}: {ten}" if ten else f"Trường hợp {i}")
        for g in giay:
            sl = []
            bc, bs = _txt(g.get("SoBanChinh")), _txt(g.get("SoBanSao"))
            if bc and bc != "0":
                sl.append(f"{bc} bản chính")
            if bs and bs != "0":
                sl.append(f"{bs} bản sao")
            out.append("- " + _txt(g.get("TenGiayTo")) + (f" ({', '.join(sl)})" if sl else ""))
    return out


def _muc_trinh_tu(d: Dict) -> List[str]:
    out = []
    for b in _ds(d.get("CacBuocThucHien")):
        if isinstance(b, dict):
            t, m = _txt(b.get("TenBuoc")), _txt(b.get("MoTa"))
            if t and m and t != m and t not in m:
                out.append(f"{t}: {m}")
            elif m or t:
                out.append(m or t)
        else:
            out.extend(_phang(b))
    return out


def _nhan_cach_thuc(c: Dict, i: int) -> str:
    nop = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop"))) or "Không ghi hình thức nộp"
    return f"{nop} — {_thoi_han(c) or 'không ghi thời hạn'} (dòng {i} của bảng cách thức nộp)"


def _muc_cach_thuc(d: Dict) -> List[str]:
    out = []
    for i, c in enumerate(_ds(d.get("CachThucThucHien")), 1):
        if not isinstance(c, dict):
            out.extend(_phang(c))
            continue
        nop = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop")))
        dong = f"- {nop or 'Không ghi hình thức nộp'}: {_thoi_han(c) or 'không ghi thời hạn'}"
        mo = _txt(c.get("MoTa"))
        if mo:
            dong += f" — {mo}"
        out.append(dong)
    return out


def _muc_noi_nop(d: Dict) -> List[str]:
    out = []
    dc = _phang(d.get("DiaChiTiepNhanHoSo"))
    if len(dc) == 1:
        out.append("Địa chỉ tiếp nhận hồ sơ: " + dc[0])
    elif dc:
        out.append("Địa chỉ tiếp nhận hồ sơ:")
        out.extend("- " + x for x in dc)
    cap = [ten for k, ten in CAP_AP_DUNG if _txt(d.get(k)).lower() == "true"]
    if cap:
        out.append("Thủ tục thực hiện ở: " + ", ".join(cap) + ".")
    ht = []
    for c in _ds(d.get("CachThucThucHien")):
        if isinstance(c, dict):
            nop = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop")))
            if nop and nop not in ht:
                ht.append(nop)
    if ht:
        out.append("Hình thức nộp hồ sơ: " + ", ".join(ht) + ".")
    return out


def _muc_le_phi(d: Dict) -> List[str]:
    """
    Mỗi khoản thu một dòng, kèm ĐỦ ngữ cảnh của dòng đó: thuộc cấp thủ tục hay
    thuộc hình thức nộp nào, thời hạn của hình thức đó, thời điểm thu. Hai
    khoản cùng mức tiền nhưng khác thời hạn là hai dòng khác nhau.
    """
    out = []

    def them(p, nhom):
        if not isinstance(p, dict):
            out.extend(_phang(p))
            return
        ten, tien, cach = _txt(p.get("TenPhi")), _tien(p), _txt(p.get("CachTinhPhi"))
        thu = _txt(p.get("ThoiDiemThu"))
        if not (ten or tien or cach or thu):
            return
        dong = "- " + (ten or "Khoản thu không ghi tên")
        dong += f": {tien}" if tien else ": nguồn không ghi số tiền"
        chi_tiet = []
        if cach:
            chi_tiet.append(f"cách tính: {cach}")
        if thu:
            chi_tiet.append(f"thời điểm thu: {M_THU.get(thu, thu)}")
        if chi_tiet:
            dong += " (" + "; ".join(chi_tiet) + ")"
        out.append(dong + f" [{nhom}]")

    for p in _ds(d.get("DanhSachPhi")):
        them(p, "ghi ở cấp thủ tục")
    for i, c in enumerate(_ds(d.get("CachThucThucHien")), 1):
        if isinstance(c, dict):
            for p in _ds(c.get("DanhSachPhi")):
                them(p, _nhan_cach_thuc(c, i))
    return out


def _muc_danh_sach(d: Dict, khoa: str, ten_con: Optional[str] = None) -> List[str]:
    """Trường dạng danh sách có tên con (TenKetQua...). Thiếu tên con thì trải toàn bộ."""
    v = d.get(khoa)
    if isinstance(v, str):
        return [v.strip()] if v.strip() else []
    out = []
    for x in _ds(v):
        if isinstance(x, dict) and ten_con and _txt(x.get(ten_con)):
            out.append("- " + _txt(x.get(ten_con)))
        else:
            out.extend("- " + t for t in _phang(x))
    return out


DUNG_MUC = {
    "ho_so": _muc_ho_so,
    "trinh_tu": _muc_trinh_tu,
    "noi_nop": _muc_noi_nop,
    "thoi_han": _muc_cach_thuc,
    "le_phi": _muc_le_phi,
    "dieu_kien": lambda d: _phang(d.get("YeuCauDieuKien")),
    "ket_qua": lambda d: _muc_danh_sach(d, "DanhSachKetQua", "TenKetQua"),
    "can_cu": lambda d: _muc_danh_sach(d, "DanhSachCanCuPhapLy", "TenCanCu"),
    "doi_tuong": lambda d: _muc_danh_sach(d, "DoiTuongThucHien", "TenDoiTuong"),
}
TEN_MUC = dict(Y_DINH_TEN, thoi_han="Cách thức nộp và thời hạn giải quyết")


def trich_muc(data: Dict, y_dinh: List[str]) -> List[Dict]:
    """Lấy các mục dữ liệu ứng với ý định. Mục trống vẫn được báo là trống."""
    out = []
    for y in y_dinh:
        dong = DUNG_MUC[y](data)
        du_lieu = {k: data.get(k) for k in TRUONG_THEO_Y_DINH[y] if k in data}
        out.append({
            "ma": y,
            "ten": TEN_MUC[y],
            "truong_goc": TRUONG_THEO_Y_DINH[y],
            "co_du_lieu": bool(dong),
            "so_dong": len(dong),
            "dong": dong,
            "du_lieu": du_lieu,
        })
    return out


# ------------------------- câu trả lời tổng hợp (16/10/2026) -------------------------
# Viết thành lời đáp cho người dân, đặt TRÊN các bảng chi tiết. Mọi dữ kiện lấy
# nguyên từ dữ liệu nguồn qua đúng các hàm trích ở trên (tên giấy tờ, số bản, số
# tiền, thời hạn); chỉ thêm câu nối cố định. Không gộp giá trị khác nhau: thời hạn
# chỉ được nói gọn “áp dụng cho cả …” khi MỌI hình thức nộp có cùng một thời hạn.
# Không dùng mô hình ngôn ngữ, nên không thể bịa dữ kiện.

def _noi(ds: List[str], cuoi: str = "và") -> str:
    ds = [x for x in ds if x]
    if len(ds) <= 1:
        return "".join(ds)
    return ", ".join(ds[:-1]) + f" {cuoi} " + ds[-1]


def _la_dung(v) -> bool:
    return _txt(v).lower() in ("true", "1", "có")


def _tt_ho_so(d: Dict) -> List[Dict]:
    """Sửa 20/10 bản 3 (F04, F05): luôn giữ tên trường hợp, kể cả khi chỉ có một trường hợp;
    dùng câu trung tính “nguồn liệt kê”, chỉ ghi “bắt buộc” khi nguồn đánh dấu BatBuoc=true
    (không suy diễn false thành được miễn nộp)."""
    cac_th = [h for h in _ds(d.get("ThanhPhanHoSo")) if isinstance(h, dict)]
    nhom = []
    for h in cac_th:
        giay = []
        for g in _ds(h.get("DanhSachGiayTo")):
            if not (isinstance(g, dict) and _txt(g.get("TenGiayTo"))):
                continue
            sl = []
            bc, bs = _txt(g.get("SoBanChinh")), _txt(g.get("SoBanSao"))
            if bc and bc != "0":
                sl.append(f"{bc} bản chính")
            if bs and bs != "0":
                sl.append(f"{bs} bản sao")
            if _la_dung(g.get("BatBuoc")):
                sl.append("nguồn ghi bắt buộc")
            if _la_dung(g.get("CoBanDienTu")):
                sl.append("có bản điện tử")
            giay.append(_txt(g.get("TenGiayTo")) + (f" ({', '.join(sl)})" if sl else ""))
        if giay:
            nhom.append((_txt(h.get("TenTruongHop")), giay))
    if not nhom:
        return []
    if len(nhom) == 1:
        ten, giay = nhom[0]
        dau = f"Trường hợp: {ten}. " if ten else ""
        return [{"loai": "p", "text": f"{dau}Nguồn liệt kê {len(giay)} loại giấy tờ trong hồ sơ:"},
                {"loai": "ds", "items": giay}]
    out = [{"loai": "p", "text": f"Hồ sơ khác nhau theo {len(nhom)} trường hợp:"}]
    for i, (ten, giay) in enumerate(nhom, 1):
        out.append({"loai": "p", "text": f"Trường hợp {i}" + (f": {ten}" if ten else "") + f" ({len(giay)} loại giấy tờ)"})
        out.append({"loai": "ds", "items": giay})
    return out


def _tt_thoi_han(d: Dict) -> List[Dict]:
    cap = []
    for c in _ds(d.get("CachThucThucHien")):
        if isinstance(c, dict):
            nop = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop"))) or "Không ghi hình thức nộp"
            cap.append((nop, _thoi_han(c) or "không ghi thời hạn", bool(_txt(c.get("MoTa")))))
    if not cap:
        return []
    ghi_chu = " Thời hạn theo từng trường hợp cụ thể có trong bảng chi tiết bên dưới." if any(x[2] for x in cap) else ""
    # gom theo hình thức nộp, giữ MỌI giá trị khác nhau của từng hình thức (không lấy một số đại diện)
    theo_nop: Dict[str, List[str]] = {}
    for nop, han, _ in cap:
        ds = theo_nop.setdefault(nop, [])
        if han not in ds:
            ds.append(han)
    han_chung = {h for ds in theo_nop.values() for h in ds}
    if len(han_chung) == 1:
        ten = [n.lower() for n in theo_nop]
        dong = f"Thời hạn giải quyết: {next(iter(han_chung))}"
        dong += (f", như nhau cho các cách nộp {_noi(ten)}" if len(ten) > 1 else f" (nộp {ten[0]})")
        return [{"loai": "p", "text": dong + "." + ghi_chu}]

    def gop(ds: List[str]) -> str:
        # “8, 10 hoặc 20 ngày làm việc” khi cùng đơn vị; khác đơn vị thì liệt kê nguyên
        m = [re.fullmatch(r"(\S+) (.+)", h) for h in ds]
        if len(ds) > 1 and all(m) and len({x.group(2) for x in m}) == 1:
            so = [x.group(1) for x in m]
            if all(re.fullmatch(r"\d+", x) for x in so):
                so.sort(key=int)
            return _noi(so, "hoặc") + " " + m[0].group(2) + " tùy trường hợp"
        return _noi(ds, "hoặc") + (" tùy trường hợp" if len(ds) > 1 else "")

    return [{"loai": "p", "text": "Thời hạn giải quyết theo cách nộp:" + ghi_chu},
            {"loai": "ds", "items": [f"{n}: {gop(ds)}" for n, ds in theo_nop.items()]}]


def _tt_noi_nop(d: Dict) -> List[Dict]:
    out = []
    ht = []
    for c in _ds(d.get("CachThucThucHien")):
        if isinstance(c, dict):
            n = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop")))
            if n and n.lower() not in ht:
                ht.append(n.lower())
    cap = [ten for k, ten in CAP_AP_DUNG if _txt(d.get(k)).lower() == "true"]
    cau = []
    if ht:
        cau.append(f"Có thể nộp hồ sơ {_noi(ht, 'hoặc')}")
    if cap:
        cau.append(f"thủ tục thực hiện ở {_noi(cap, 'hoặc')}")
    if cau:
        out.append({"loai": "p", "text": "; ".join(cau) + "."})
    dc = _phang(d.get("DiaChiTiepNhanHoSo"))
    if len(dc) == 1:
        out.append({"loai": "p", "text": "Địa chỉ tiếp nhận hồ sơ: " + dc[0]})
    elif dc:
        out += [{"loai": "p", "text": "Địa chỉ tiếp nhận hồ sơ:"}, {"loai": "ds", "items": dc}]
    return out


def _tt_le_phi(d: Dict) -> List[Dict]:
    dong = []

    def them(p, ngu_canh):
        if not isinstance(p, dict):
            dong.extend(_phang(p))
            return
        # Sửa 20/10 bản 3 (F03): giữ nguyên văn cách tính phí và thời điểm thu; khoản chỉ có
        # cách tính hoặc thời điểm thu vẫn được nêu, không bị coi là “nguồn không ghi phí”.
        ten, tien, thu = _txt(p.get("TenPhi")), _tien(p), _txt(p.get("ThoiDiemThu"))
        cach = _txt(p.get("CachTinhPhi"))
        if not (ten or tien or cach or thu):
            return
        t = (ten or "Khoản thu không ghi tên") + ": " + (tien or "nguồn không ghi số tiền")
        phu = []
        if cach:
            phu.append(f"cách tính: {cach}")
        if thu:
            phu.append(f"thu {M_THU.get(thu, thu)}")
        if ngu_canh:
            phu.append(ngu_canh)
        dong.append(t + (f" ({'; '.join(phu)})" if phu else ""))

    for p in _ds(d.get("DanhSachPhi")):
        them(p, "")
    for c in _ds(d.get("CachThucThucHien")):
        if isinstance(c, dict):
            nop = M_NOP.get(_txt(c.get("HinhThucNop")), _txt(c.get("HinhThucNop")))
            for p in _ds(c.get("DanhSachPhi")):
                them(p, f"khi nộp {nop.lower()}, thời hạn {_thoi_han(c) or 'không ghi'}" if nop else "")
    if not dong:
        return []
    return [{"loai": "p", "text": f"Phí, lệ phí ({len(dong)} khoản):" if len(dong) > 1 else "Phí, lệ phí:"},
            {"loai": "ds", "items": dong}]


PHI_TOI_DA_TONG_QUAN = 8


def _tt_le_phi_tong_quan(d: Dict) -> List[Dict]:
    """Câu hỏi chung chung: nhiều khoản phí thì chỉ báo số khoản và chỉ cách xem đủ, không chọn ra vài khoản."""
    k = _tt_le_phi(d)
    if k and len(k[1]["items"]) > PHI_TOI_DA_TONG_QUAN:
        return [{"loai": "p", "text": (f"Thủ tục có {len(k[1]['items'])} khoản phí, lệ phí, khác nhau theo đối tượng và "
                                       "cách nộp. Hỏi “lệ phí bao nhiêu” để xem đủ từng khoản, hoặc mở bảng chi tiết bên dưới.")}]
    return k


def _tt_danh_sach(nhan: str, dong: List[str]) -> List[Dict]:
    dong = [x[2:] if x.startswith("- ") else x for x in dong]
    if not dong:
        return []
    if len(dong) == 1:
        return [{"loai": "p", "text": f"{nhan}: {dong[0].rstrip('.')}."}]
    return [{"loai": "p", "text": f"{nhan}:"}, {"loai": "ds", "items": dong}]


TOM_TAT = {
    "ho_so": _tt_ho_so,
    "thoi_han": _tt_thoi_han,
    "noi_nop": _tt_noi_nop,
    "le_phi": _tt_le_phi,
    "doi_tuong": lambda d: _tt_danh_sach("Đối tượng thực hiện", DUNG_MUC["doi_tuong"](d)),
    "ket_qua": lambda d: _tt_danh_sach("Kết quả nhận được", DUNG_MUC["ket_qua"](d)),
    "trinh_tu": lambda d: _tt_danh_sach("Các bước thực hiện", DUNG_MUC["trinh_tu"](d)),
    "dieu_kien": lambda d: _tt_danh_sach("Điều kiện", DUNG_MUC["dieu_kien"](d)),
    "can_cu": lambda d: _tt_danh_sach("Căn cứ pháp lý", DUNG_MUC["can_cu"](d)),
}
# Câu hỏi chung chung (“thủ tục X làm thế nào”): trả lời đủ những gì người dân cần biết trước khi đi nộp.
TOM_TAT_TONG_QUAN = ["doi_tuong", "ho_so", "noi_nop", "thoi_han", "le_phi", "ket_qua"]


def tong_hop(doc, y_dinh: List[str]) -> Dict:
    """Dựng câu trả lời tổng hợp: một câu mở đầu và các khối đoạn văn / danh sách."""
    data = doc.data or {}
    cac_y = y_dinh or TOM_TAT_TONG_QUAN
    khoi: List[Dict] = []
    trong = []
    for y in cac_y:
        k = _tt_le_phi_tong_quan(data) if (y == "le_phi" and not y_dinh) else TOM_TAT[y](data)
        if k:
            khoi.extend(k)
        elif y_dinh:
            trong.append(TEN_MUC[y].lower())
    if not y_dinh and not _tt_le_phi(data):
        trong.append("phí, lệ phí")          # câu hỏi chung: vẫn nói rõ nguồn không ghi phí (không suy ra “miễn phí”)
    if trong:
        khoi.append({"loai": "p", "text": f"Dữ liệu nguồn không ghi {_noi(trong)} cho thủ tục này."})
    ten, cq = getattr(doc, "title", "") or "", getattr(doc, "agency", None)
    mo_dau = f"Theo dữ liệu thủ tục “{ten}”" + (f" ({cq})" if cq else "") + ":"
    return {"mo_dau": mo_dau, "khoi": khoi}


def _the_thu_tuc(doc, phan_tram=None) -> Dict:
    data = doc.data or {}
    return {
        "id": doc.id,
        "ma_thu_tuc": doc.procedure_code,
        "ten": doc.title,
        "co_quan": doc.agency,
        "linh_vuc": doc.category,
        "do_khop": phan_tram,
        "ngung_ap_dung": _txt(data.get("TrangThai")) == "INACTIVE",
        # 21/10 bản 2: cấp thực hiện, để người dùng phân biệt các lựa chọn có tên gần giống nhau
        "cap_ap_dung": [ten for k, ten in CAP_AP_DUNG if _txt(data.get(k)).lower() == "true"],
    }


# ------------------------- lớp mô hình ngôn ngữ (tùy chọn) -------------------------

def ngu_canh_loi_dan(doc, muc: List[Dict]) -> str:
    """
    Ngữ cảnh cho mô hình viết LỜI DẪN. Cố ý KHÔNG đưa dữ kiện (giấy tờ, số tiền,
    thời hạn...) vào: mô hình không có dữ kiện thì không thể diễn đạt sai dữ kiện.
    Chỉ có tên thủ tục, cơ quan và tên các mục sẽ hiển thị bên dưới.
    """
    # Sửa 14/10: không đưa danh sách "mục nguồn không ghi" cho mô hình nữa. Hệ thống
    # tự báo mục trống ở từng mục; lời dẫn không cần (và không được) nói về chúng.
    co = [m["ten"] for m in muc if m["co_du_lieu"]]
    return "\n".join([
        f"TÊN THỦ TỤC: {doc.title}",
        f"CƠ QUAN: {doc.agency or ''}",
        "CÁC MỤC SẼ HIỂN THỊ NGAY BÊN DƯỚI LỜI DẪN: " + ("; ".join(co) or "(không có)"),
    ])


CHU_SO = re.compile(r"\d")
# Từ chỉ số lượng, đơn vị, và các khẳng định thường gặp khi mô hình "bịa" dữ kiện.
# Danh sách cố ý rộng: loại nhầm một lời dẫn vô hại chỉ làm hệ thống quay về
# lời dẫn khuôn mẫu, còn lọt một dữ kiện sai thì người dân bị hướng dẫn sai.
TU_CAM = [
    "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười", "mươi", "trăm",
    "nghìn", "ngàn", "triệu", "tỷ", "tỉ", "lăm", "mốt", "rưỡi", "nửa", "vài", "mấy",
    "đồng", "vnđ", "vnd", "usd", "ngày", "tháng", "tuần", "giờ", "phút", "phần trăm",
    "miễn", "không cần", "không phải", "không mất", "không thu", "không yêu cầu", "chỉ cần",
    "bắt buộc", "tối đa", "tối thiểu", "ít nhất", "nhiều nhất", "trong vòng", "chậm nhất",
    "bản chính", "bản sao", "http", "www",
]
LOI_DAN_TOI_DA = 400

# Sửa 14/10/2026: DANH SÁCH CHO PHÉP thay cho việc chỉ dựa vào danh sách cấm.
# Danh sách cấm không chặn được câu không có số như “Nộp hồ sơ tại Đại sứ quán”,
# “Ho so khong can giay to” hay câu tiếng Anh. Nay MỌI âm tiết của lời dẫn phải
# thuộc một trong ba nguồn: tên thủ tục, tên cơ quan và tên các mục sẽ hiển thị
# (lấy từ chính dữ liệu), hoặc bộ từ nối cố định dưới đây. Từ nối cố ý không có
# “không”, “tại”, “miễn”, tên địa điểm, tên giấy tờ: lời dẫn chỉ được giới
# thiệu, mọi khẳng định là việc của các mục trích từ nguồn.
TU_NOI_LOI_DAN = frozenset("""
dưới đây là các những mục thông tin về của cho thủ tục bạn hỏi trích từ theo dữ liệu
nguồn được hiển thị bên sau gồm và hoặc phần nội dung tham khảo xem có thể chi tiết
cụ thể liên quan này đó như chính thức cổng dịch vụ công quốc gia hệ thống trang đã
đang tương ứng mời vui lòng trên câu tìm thấy tra cứu lưu ý đối chiếu với quan tâm do
quản lý thuộc ban hành
""".split())


def _am_tiet(s: str) -> List[str]:
    """Các âm tiết chữ (bỏ số, dấu câu), viết thường, chuẩn NFC."""
    return re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", s or "").lower())


def kiem_tra_loi_dan(van_ban: str, ten_thu_tuc: str = "", ngu_canh: Iterable[str] = ()) -> Dict:
    """
    Lời dẫn do mô hình viết chỉ được giới thiệu, KHÔNG được nêu dữ kiện. Kiểm
    tra: không có chữ số, không có từ trong TU_CAM (so theo ranh giới từ, có
    dấu), không dài quá LOI_DAN_TOI_DA ký tự, và (từ 14/10) mọi âm tiết phải
    nằm trong danh sách cho phép. Không dùng con số hay từ ngữ trong câu hỏi
    của người dùng làm bằng chứng cho bất cứ điều gì.

    Từ 15/10: tên thủ tục và mỗi mục trong `ngu_canh` (tên cơ quan, tên các mục
    sẽ hiển thị) chỉ được nhắc NGUYÊN CỤM. Trước đây từng âm tiết của các tên
    này đều được phép riêng lẻ, nên câu ghép lại như “Hồ sơ gồm hộ chiếu phổ
    thông.” (thủ tục “Cấp hộ chiếu phổ thông”, mục “Thành phần hồ sơ”) vẫn lọt.
    Đây vẫn chỉ là ràng buộc từ vựng, không phải kiểm chứng ngữ nghĩa.
    """
    ly_do = []
    t = unicodedata.normalize("NFC", (van_ban or "").strip())
    # Tên thủ tục được phép nhắc nguyên văn (có thể chứa số, ví dụ "dưới 6 tuổi"):
    # bỏ đúng chuỗi tên khỏi phần cần kiểm tra, mọi chỗ khác vẫn bị kiểm tra.
    ten = unicodedata.normalize("NFC", (ten_thu_tuc or "").strip())
    kiem = re.sub(re.escape(ten), " ", t, flags=re.IGNORECASE) if ten else t
    if not t:
        ly_do.append("lời dẫn rỗng")
    if len(t) > LOI_DAN_TOI_DA:
        ly_do.append(f"dài quá {LOI_DAN_TOI_DA} ký tự")
    if CHU_SO.search(kiem):
        ly_do.append("có chữ số")
    thuong = " " + re.sub(r"[^\wà-ỹđ]+", " ", kiem.lower()) + " "
    gap = [w for w in TU_CAM if f" {w} " in thuong]
    if gap:
        ly_do.append("có từ chỉ dữ kiện: " + ", ".join(gap))
    # Bỏ các tên được phép (nguyên cụm, dài trước ngắn sau); phần còn lại chỉ được là từ nối.
    con_lai = " " + " ".join(_am_tiet(kiem)) + " "
    cum = {" ".join(_am_tiet(x)) for x in [ten, *(ngu_canh or ())] if x}
    for c in sorted((c for c in cum if c), key=len, reverse=True):
        con_lai = con_lai.replace(f" {c} ", " ")
        con_lai = con_lai.replace(f" {c} ", " ")   # lần hai cho hai cụm liền nhau
    la: List[str] = []
    for w in con_lai.split():
        if w not in TU_NOI_LOI_DAN and w not in la:
            la.append(w)
    if la:
        ly_do.append("có từ ngoài ngữ cảnh: " + ", ".join(la[:6]) + (" …" if len(la) > 6 else ""))
    return {"dat": not ly_do, "ly_do": ly_do}


def viet_loi_dan_bang_mo_hinh(kq: Dict, doc, cau_hoi: str) -> None:
    """Gọi mô hình viết lời dẫn; đạt kiểm tra thì thay lời dẫn khuôn mẫu. Ghi kết quả vào kq."""
    if not (llm.da_bat() and kq.get("trang_thai") == "tra_loi" and kq.get("muc")):
        return
    van_ban, loi = llm.viet_loi_dan(cau_hoi, ngu_canh_loi_dan(doc, kq["muc"]))
    kq["mo_hinh"] = llm.ten_mo_hinh()
    if not van_ban:
        kq["kiem_chung"] = {"dat": False, "ly_do": [f"không gọi được mô hình ({loi})"]}
        return
    kc = kiem_tra_loi_dan(van_ban, doc.title,
                          [doc.agency or ""] + [m["ten"] for m in kq["muc"] if m["co_du_lieu"]])
    kq["kiem_chung"] = kc
    if kc["dat"]:
        kq["loi_dan_khuon_mau"] = kq["tra_loi"]
        kq["tra_loi"] = van_ban
        kq["nguon_tra_loi"] = "mo_hinh_ngon_ngu"


def _loi_dan(doc, muc: List[Dict], hoi_cu_the: bool) -> str:
    co = [m for m in muc if m["co_du_lieu"]]
    thieu = [m["ten"].lower() for m in muc if not m["co_du_lieu"]]
    cau = f"Theo dữ liệu của Cổng Dịch vụ công Quốc gia, thủ tục “{doc.title}”"
    if doc.procedure_code:
        cau += f" (mã {doc.procedure_code})"
    if co:
        cau += " có thông tin như sau." if not hoi_cu_the else \
            " có thông tin về " + ", ".join(m["ten"].lower() for m in co) + " như sau."
    else:
        cau += " hiện chưa có dữ liệu cho nội dung bạn hỏi."
    if thieu and co:
        cau += " Nguồn dữ liệu không ghi: " + ", ".join(thieu) + "."
    return cau


# ------------------------- hỏi lại khi các thủ tục gần giống nhau (21/10/2026) -------------------------
# Báo cáo kiểm thử độc lập F07: trợ lý khẳng định theo thủ tục sai với độ khớp 100% khi nhiều thủ tục
# cùng chứa mọi từ của câu hỏi (“làm hộ chiếu” → hộ chiếu NGOẠI GIAO; “đăng ký tàu cá” → XÓA đăng ký).
# Quy tắc dưới đây giải được ca “tàu cá”; ca “hộ chiếu” CHƯA giải được (xem tài liệu 17, mục 2.1).
# Độ khớp chỉ đo câu hỏi có nằm trong tên thủ tục không, không đo tên thủ tục có thêm điều câu hỏi
# KHÔNG nói. Quy tắc: thủ tục đứng đầu bị coi là “chưa chắc” nếu có một thủ tục khác điểm sát nó
# (≥ NGUONG_GAN_NHAU lần điểm của nó) và
#   (a) tên thủ tục đứng đầu có từ SO_TU_KHAC_BIET từ nội dung trở lên mà câu hỏi không nói và thủ tục
#       kia không có (ví dụ “ngoại giao, công vụ”, “nhà máy điện hạt nhân”), hoặc
#   (b) tên thủ tục đứng đầu có một từ chỉ hành động khác (xóa, chấm dứt, gia hạn, cấp lại…) mà câu hỏi
#       không nói và thủ tục kia không có.
# Khi đó trợ lý HỎI LẠI kèm các lựa chọn thay vì khẳng định. Hai tham số được chọn trên TẬP PHÁT TRIỂN
# (bo_de_phat_trien_NHAN_DE_XUAT.csv) theo tiêu chí đặt trước: giảm số câu trả lời sai ít nhất một nửa,
# trong các cấu hình đạt thì chọn cấu hình hỏi lại ít nhất. Bộ kiểm tra độc lập và bộ trợ lý chỉ dùng để
# báo cáo. Xem 17_DANH_GIA_VA_HOAN_THIEN_20261021.md.
NGUONG_GAN_NHAU = 0.90
SO_TU_KHAC_BIET = 3
TU_HANH_DONG = ["xóa", "chấm dứt", "tạm dừng", "tạm ngừng", "thôi", "hủy", "thu hồi", "gia hạn", "cấp đổi",
                "cấp lại", "đổi", "điều chỉnh", "sửa đổi", "thay đổi", "giải thể", "ngừng", "chuyển"]
_HU_TU = {"thu", "tuc", "viec", "doi", "voi", "cua", "cho", "tai", "o", "va", "cac", "ve", "theo", "la", "duoc",
          "co", "da", "khi", "tu", "tren", "do", "moi", "trong", "hoac"}


def _bo_dau_thuong(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")


def _tu_noi_dung(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", _bo_dau_thuong(s)) if w not in _HU_TU}


def _co_cum(van_ban: str, cum: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(cum) + r"(?!\w)", van_ban) is not None


def ly_do_chua_chac(cau_hoi: str, xep_hang, bien_the: Optional[List[str]] = None) -> Optional[str]:
    """Trả về lý do (chuỗi) nếu thủ tục đứng đầu chưa đủ chắc để khẳng định; None nếu đủ chắc."""
    if len(xep_hang) < 2:
        return None
    cac_cau = list(bien_the or []) + [cau_hoi]
    tu_hoi = set().union(*(_tu_noi_dung(c) for c in cac_cau))
    cau_thuong = " ".join(c.lower() for c in cac_cau)
    cau_khong_dau = _bo_dau_thuong(cau_thuong)
    dau, diem_dau = xep_hang[0][0], xep_hang[0][1]
    ten_dau = (dau.title or "").lower()
    du_dau = _tu_noi_dung(dau.title) - tu_hoi
    gan = [d for d, diem, _ in xep_hang[1:5] if diem >= NGUONG_GAN_NHAU * diem_dau]
    for d in gan:
        if len(du_dau - (_tu_noi_dung(d.title) - tu_hoi)) >= SO_TU_KHAC_BIET:
            return "ten_gan_giong"
        for h in TU_HANH_DONG:
            if (_co_cum(ten_dau, h) and not _co_cum(cau_thuong, h) and not _co_cum(cau_khong_dau, _bo_dau_thuong(h))
                    and not _co_cum((d.title or "").lower(), h)):
                return "hanh_dong_khac"
    return None


# ------------------------- ưu tiên thủ tục đang áp dụng (24/10/2026) -------------------------
# Thử trên máy chủ thật: “cấp lại căn cước bị mất lệ phí bao nhiêu” được trả lời theo thủ tục “Cấp lại thẻ căn
# cước” đang NGỪNG ÁP DỤNG, trong khi ngay dưới nó có các thủ tục “Cấp, cấp đổi, cấp lại thẻ căn cước” đang áp
# dụng. Trợ lý chỉ cảnh báo nhưng vẫn đọc lệ phí của thủ tục đã ngừng. Quy tắc: nếu thủ tục đứng đầu ngừng áp dụng
# và trong SO_LUA_CHON thủ tục đầu có thủ tục KHÔNG ngừng áp dụng với độ khớp ≥ NGUONG_TRA_LOI và không thấp hơn
# thủ tục đầu quá CHENH_LECH_NGUNG điểm, trợ lý HỎI LẠI, xếp các thủ tục đang áp dụng lên trước. Không sửa search.py
# (thứ hạng tra cứu và mọi số đo giữ nguyên); người dùng vẫn chọn được thủ tục đã ngừng nếu muốn.
# CHENH_LECH_NGUNG đặt theo nguyên tắc (rộng hơn mức 5 điểm của lời nhắc “tên gần giống”), CHƯA được hiệu chỉnh
# trên bộ đề: kho dùng cho các bộ đo không có trường trạng thái nên quy tắc không ảnh hưởng tới số đo đã báo cáo.
CHENH_LECH_NGUNG = 10


def _ngung(doc) -> bool:
    return _txt((getattr(doc, "data", None) or {}).get("TrangThai")) == "INACTIVE"


def thu_tuc_dang_ap_dung_thay_the(xep_hang) -> List:
    """Các thủ tục đang áp dụng nên được ưu tiên hơn thủ tục đứng đầu đã ngừng áp dụng; [] nếu không có."""
    if not xep_hang or not _ngung(xep_hang[0][0]):
        return []
    p_dau = xep_hang[0][2] or 0
    return [(d, s, p) for d, s, p in xep_hang[1:SO_LUA_CHON]
            if not _ngung(d) and (p or 0) >= NGUONG_TRA_LOI and (p or 0) >= p_dau - CHENH_LECH_NGUNG]


def tra_loi(cau_hoi: str, docs: List, doc_chi_dinh=None, dung_mo_hinh: bool = True, nap_day_du=None) -> Dict[str, Any]:
    """
    Trả lời một câu hỏi. `doc_chi_dinh`: người dùng đã chọn sẵn một thủ tục
    (bấm vào lựa chọn trợ lý đưa ra) thì bỏ qua bước truy xuất.
    """
    t0 = time.perf_counter()
    # Giao tiếp cơ bản (16/10): cả câu chỉ là lời chào/cám ơn/tạm biệt → đáp lại, không tra cứu.
    if doc_chi_dinh is None:
        loai = giao_tiep.nhan_dien(cau_hoi)
        if loai:
            gt = giao_tiep.tra_loi_giao_tiep(loai)
            return {"cau_hoi": cau_hoi, "trang_thai": "giao_tiep", "giao_tiep": loai,
                    "tra_loi": gt["tra_loi"], "goi_y": gt["goi_y"], "hieu": {}, "nguon_tra_loi": "khuon_mau",
                    "mo_hinh": None, "kiem_chung": None, "muc": [], "thu_tuc": None, "lua_chon": [], "nguon": [],
                    "thoi_gian_ms": round((time.perf_counter() - t0) * 1000, 1)}
    cau_goc = cau_hoi
    cau_hoi, chao = giao_tiep.boc_loi_chao(cau_hoi)
    pt = phan_tich(cau_hoi)
    y_dinh = [y for y in pt["y_dinh"] if y in DUNG_MUC]
    kq: Dict[str, Any] = {
        "cau_hoi": cau_goc,
        "chao": chao,
        "hieu": {
            "chu_de": pt["chu_de"],
            "tu_dem": pt["tu_dem"],
            "dong_nghia": [{"tu": a, "thanh": b} for a, b in pt["dong_nghia"]],
            "y_dinh": [{"ma": y, "ten": TEN_MUC[y]} for y in y_dinh],
        },
        "nguon_tra_loi": "trich_xuat",
        "mo_hinh": None,
        "kiem_chung": None,
        "muc": [],
        "thu_tuc": None,
        "lua_chon": [],
        "nguon": [],
    }

    if doc_chi_dinh is not None:
        doc, phan_tram, khac = doc_chi_dinh, None, []
    else:
        xep_hang, _ = search_module.search_chi_tiet(cau_hoi, docs, limit=SO_LUA_CHON + SO_TUONG_TU)
        if not xep_hang:
            kq.update(trang_thai="ngoai_pham_vi", tra_loi=(
                "Tôi không tìm thấy thủ tục hành chính nào phù hợp với câu hỏi này trong kho dữ liệu. "
                "Tôi chỉ trả lời được về thủ tục hành chính có trên Cổng Dịch vụ công Quốc gia. "
                "Bạn thử nêu tên thủ tục hoặc giấy tờ cần làm, ví dụ: “đăng ký khai sinh cần giấy tờ gì”."))
            kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return kq
        dau = xep_hang[0]
        if dau[2] < NGUONG_TRA_LOI:
            kq.update(trang_thai="can_lam_ro", tra_loi=(
                "Tôi chưa chắc bạn đang hỏi về thủ tục nào. Dưới đây là các thủ tục gần nhất với câu hỏi; "
                "bạn chọn một thủ tục để tôi trả lời chính xác, hoặc hỏi lại bằng tên thủ tục."))
            kq["lua_chon"] = [_the_thu_tuc(d, p) for d, _, p in xep_hang[:SO_LUA_CHON]]
            kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return kq
        thay_the = thu_tuc_dang_ap_dung_thay_the(xep_hang)
        if thay_the:
            kq.update(trang_thai="can_lam_ro", ly_do_hoi_lai="ngung_ap_dung", tra_loi=(
                f"Thủ tục khớp nhất với câu hỏi, “{dau[0].title}”, đang ở trạng thái NGỪNG ÁP DỤNG theo dữ liệu nguồn, "
                "trong khi có thủ tục đang áp dụng với tên gần giống. Bạn chọn thủ tục phù hợp để tôi trả lời; "
                "các thủ tục đang áp dụng được xếp trước."))
            kq["lua_chon"] = [_the_thu_tuc(d, p) for d, _, p in thay_the] + [_the_thu_tuc(dau[0], dau[2])]
            kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return kq
        ly_do = ly_do_chua_chac(cau_hoi, xep_hang, pt.get("bien_the"))
        if ly_do:
            kq.update(trang_thai="can_lam_ro", ly_do_hoi_lai=ly_do, tra_loi=(
                "Có nhiều thủ tục chứa đúng các từ trong câu hỏi nhưng khác nhau về đối tượng, cơ quan hoặc việc "
                "cần làm (ví dụ cấp mới, cấp lại hay xóa). Bạn chọn đúng thủ tục để tôi trả lời chính xác. "
                "Nếu chưa thấy thủ tục mình cần, hãy hỏi lại kèm đối tượng, ví dụ “hộ chiếu phổ thông”."))
            kq["lua_chon"] = [_the_thu_tuc(d, p) for d, _, p in xep_hang[:SO_LUA_CHON]]
            kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return kq
        doc, phan_tram = dau[0], dau[2]
        khac = [_the_thu_tuc(d, p) for d, _, p in xep_hang[1:1 + SO_TUONG_TU]]
        # Kho trong bộ nhớ có thể chỉ giữ bản ghi gọn (main._BanGhiGon): đọc bản đầy đủ từ database.
        if nap_day_du is not None:
            doc = nap_day_du(doc) or doc

    data = doc.data or {}
    hoi_cu_the = bool(y_dinh)
    muc = trich_muc(data, y_dinh or Y_DINH_TONG_QUAN) if data else []
    if not hoi_cu_the:
        muc = [m for m in muc if m["co_du_lieu"]]
    kq.update(trang_thai="tra_loi", thu_tuc=_the_thu_tuc(doc, phan_tram), lua_chon=khac, muc=muc)
    if not data:
        kq["tra_loi"] = (f"Tôi tìm thấy thủ tục “{doc.title}” nhưng bản ghi này chưa có dữ liệu chi tiết "
                         "trong kho. Bạn mở trang chi tiết để xem thông tin hiện có.")
    elif data.get("NguonDuLieu") == "CAN_BO_BIEN_TAP":
        kq["tra_loi"] = f"Hướng dẫn “{doc.title}” do cán bộ biên soạn. Nội dung:\n\n" + _txt(data.get("NoiDungHuongDan"))
        kq["muc"] = []
    else:
        kq["tra_loi"] = _loi_dan(doc, muc, hoi_cu_the)
        kq["tom_tat"] = tong_hop(doc, y_dinh)
        if khac and phan_tram is not None and khac[0]["do_khop"] is not None and khac[0]["do_khop"] >= phan_tram - 5:
            kq["luu_y"] = ("Có nhiều thủ tục có tên gần giống nhau (khác cấp thực hiện hoặc đối tượng). "
                           "Tôi trả lời theo thủ tục khớp nhất; bạn kiểm tra danh sách “Thủ tục tương tự” bên dưới.")
        if dung_mo_hinh:
            viet_loi_dan_bang_mo_hinh(kq, doc, cau_hoi)
    if data.get("TrangThai") == "INACTIVE":
        kq["luu_y"] = (kq.get("luu_y", "") + " Theo dữ liệu nguồn, thủ tục này đang ở trạng thái NGỪNG ÁP DỤNG.").strip()
    kq["nguon"] = [{
        "id": doc.id, "ma_thu_tuc": doc.procedure_code, "ten": doc.title,
        "noi_cung_cap": "Cổng Dịch vụ công Quốc gia" if data.get("NguonDuLieu") != "CAN_BO_BIEN_TAP" else "Cán bộ biên soạn",
        "muc": [m["ten"] for m in kq["muc"] if m["co_du_lieu"]],
        "truong_goc": sorted({t for m in kq["muc"] if m["co_du_lieu"] for t in m["truong_goc"]}),
    }]
    kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return kq
