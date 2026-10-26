"""Đối chiếu ĐỘC LẬP câu trả lời của trợ lý với dữ liệu JSON gốc (bổ sung 09/10/2026).

Vì sao cần: phép đo cũ dựng "nguồn" bằng chính hàm đã dựng câu trả lời, nên hai
lần dựng giống nhau là điều hiển nhiên; nó không phát hiện được hàm trích bỏ
sót hay ghép sai. Module này KHÔNG import bất cứ thứ gì từ app/tro_ly.py. Nó tự
đọc JSON gốc theo định nghĩa riêng và kiểm tra hai chiều:

  1. ĐỘ BAO PHỦ: mỗi dữ kiện có trong nguồn phải xuất hiện trong câu trả lời,
     đếm theo SỐ LẦN (nguồn có hai giấy tờ trùng tên thì câu trả lời phải có
     hai dòng). Với lệ phí nằm trong một hình thức nộp, dòng trả lời phải ghi
     cả số tiền LẪN thời hạn của hình thức đó (giữ quan hệ phí–thời hạn).
  2. CĂN CỨ: mỗi dòng của câu trả lời phải chứa ít nhất một chuỗi có thật
     trong phần nguồn tương ứng (không có dòng "từ trên trời rơi xuống").

Giới hạn (ghi rõ để không đọc quá mức): so khớp theo CHUỖI. Nó bắt được việc
bỏ sót, cắt bớt, tách rời phí khỏi thời hạn; nó không đánh giá văn phong và
không thay được việc người đọc kiểm tra ngữ nghĩa.

Phiên bản DC-20261014-2 (bản chặt). Bản 09/10 chỉ so TÊN và CHỮ SỐ nên nhận
“3 tháng” khi nguồn ghi 3 ngày làm việc, “125.000 USD” khi nguồn ghi đồng, hay
“99 bản chính”. Bản này thêm:
  3. ĐỦ CỤM: dữ kiện thời hạn phải có cả số lẫn đơn vị (“3 ngày làm việc”); dữ
     kiện phí phải có số tiền kèm đơn vị tiền, thời điểm thu và (nếu thuộc một
     hình thức nộp) thời hạn kèm đơn vị; giấy tờ phải có đúng “N bản chính”,
     “M bản sao” khi nguồn ghi số bản.
  4. KHÔNG KHẲNG ĐỊNH SAI: mọi cặp số–đơn vị (thời gian, tiền, số bản) xuất hiện
     trong một dòng trả lời phải có trong nguồn của mục đó. Một dòng có tên
     đúng nhưng kèm “3 tháng” sai vẫn bị bắt, dù dòng đó có “căn cứ” theo chuỗi.

Phiên bản DC-20261015-1 (sửa sau rà soát độc lập 15/10). Bản 14/10 chỉ hỏi “cặp
số–đơn vị này có ở đâu đó trong mục không”, nên nếu Tờ khai A cần 1 bản chính và
Văn bản B cần 2 bản chính, thêm dòng “Tờ khai A (2 bản chính)” vẫn lọt. Bản này thêm:
  5. ĐÚNG CHỦ THỂ: khi một dòng nhắc tên một giấy tờ, một khoản phí hoặc một hình
     thức nộp có trong nguồn, các cặp số–đơn vị thuộc loại mà chủ thể đó quy định
     (số bản của giấy tờ; số tiền của khoản phí; thời hạn và phí của hình thức
     nộp) phải là của CHÍNH chủ thể đó. Tên ngắn nằm trong tên dài hơn cùng xuất
     hiện (ví dụ “Trực tuyến” trong tên phí) thì chỉ tính tên dài.
  Hai hình thức nộp trùng tên (hai dòng “Trực tiếp” cho hai trường hợp) được tách
  theo phần mô tả nếu dòng trả lời chép mô tả đó. Giới hạn còn lại: hai giấy tờ
  hoặc hai khoản phí trùng tên được gộp chung; dòng không nhắc tên chủ thể nào chỉ
  được kiểm theo điểm 4.
Chạy `python kiem_tra_bo_doi_chieu.py` để xem bộ này bắt được bao nhiêu lỗi cố ý.
"""
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Set, Tuple

PHIEN_BAN = "DC-20261021-1"

# Bảng tra RIÊNG của bộ đối chiếu (cố ý không dùng bảng của tro_ly.py)
_NOP = {"DIRECT": "Trực tiếp", "ONLINE": "Trực tuyến", "POSTAL": "Qua bưu điện",
        "BKAV": "Dịch vụ bưu chính", "EMAIL": "Qua email", "FAX": "Qua fax"}
_CAP = {"ApDungCapXa": "cấp xã", "ApDungCapTinh": "cấp tỉnh", "ApDungCapBo": "cấp bộ",
        "ApDungCoQuanKhac": "cơ quan khác", "ApDungCoQuanNganhDoc": "cơ quan ngành dọc"}
_DV = {"WORKING_DAY": "ngày làm việc", "DAY": "ngày", "MONTH": "tháng", "HOUR": "giờ",
       "YEAR": "năm", "MINUTE": "phút", "WEEK": "tuần"}
_TIEN = {"VND": "đồng", "USD": "usd"}
_THU = {"AT_RESULT_COLLECTION": "khi nhận kết quả", "AT_SUBMISSION": "khi nộp hồ sơ"}

# Cặp số–đơn vị tìm trong một dòng (đơn vị dài đặt trước để “ngày làm việc” không bị cắt thành “ngày”)
_RE_THOI_GIAN = re.compile(r"(\d[\d.,]*)\s*(ngày làm việc|ngày|tháng|năm|giờ|phút|tuần)(?![\wà-ỹđ])")
_RE_TIEN = re.compile(r"(\d[\d.,]*)\s*(đồng|vnđ|vnd|usd)(?![\wà-ỹđ])")
_RE_BAN = re.compile(r"(\d+)\s*(bản chính|bản sao)")
_DONG_TIEN = {"vnđ": "đồng", "vnd": "đồng"}


def _n(s) -> str:
    s = unicodedata.normalize("NFC", "" if s is None else str(s))
    return re.sub(r"\s+", " ", s).strip().lower()


def _so(s) -> str:
    return re.sub(r"\D", "", "" if s is None else str(s))


def _ds(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def _han(c: Dict) -> str:
    """“3 ngày làm việc”: số và đơn vị đọc thẳng từ nguồn (đơn vị lạ giữ nguyên mã)."""
    n, dv = _n(c.get("ThoiGianXuLy")), str(c.get("DonViThoiGian") or "").strip()
    return f"{n} {_n(_DV.get(dv, dv))}".strip() if n else ""


def _tien_cum(p: Dict) -> str:
    """“125.000 đồng”: định dạng số nguyên có dấu chấm hàng nghìn; số lạ giữ nguyên."""
    raw = str(p.get("SoTien") or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"-?\d+", raw):
        raw = f"{int(raw):,}".replace(",", ".")
    ma = str(p.get("MaTienTe") or "").strip()
    return _n(f"{raw} {_TIEN.get(ma, ma)}")


def _cap(dong_n: str) -> Set[Tuple[str, str]]:
    """Mọi cặp (chữ số, đơn vị) về thời gian, tiền, số bản có trong một chuỗi đã chuẩn hóa."""
    out = set()
    for so, dv in _RE_THOI_GIAN.findall(dong_n):
        out.add((_so(so).lstrip("0") or "0", dv))
    for so, dv in _RE_TIEN.findall(dong_n):
        out.add((_so(so).lstrip("0") or "0", _DONG_TIEN.get(dv, dv)))
    for so, dv in _RE_BAN.findall(dong_n):
        out.add((so.lstrip("0") or "0", dv))
    return out


def _loai(dv: str) -> str:
    return "ban" if dv in ("bản chính", "bản sao") else "tien" if dv in ("đồng", "usd") else "thoi_gian"


def _thuc_the(data: Dict, y: str) -> List[Tuple[str, Set[str], Set[Tuple[str, str]], str]]:
    """Các chủ thể có tên trong nguồn của mục `y`:
    (tên chuẩn hóa, loại cặp nó quy định, cặp của nó, mô tả kèm để phân biệt hai chủ thể trùng tên)."""
    out = []
    if y == "ho_so":
        for h in _ds(data.get("ThanhPhanHoSo")):
            for g in (_ds(h.get("DanhSachGiayTo")) if isinstance(h, dict) else []):
                if isinstance(g, dict) and _n(g.get("TenGiayTo")):
                    cap = set()
                    for f, ten in (("SoBanChinh", "bản chính"), ("SoBanSao", "bản sao")):
                        so = _so(g.get(f)).lstrip("0")
                        if so:
                            cap.add((so, ten))
                    out.append((_n(g["TenGiayTo"]), {"ban"}, cap, ""))
    if y in ("le_phi", "thoi_han"):
        def phi(p):
            ten = _n(p.get("TenPhi"))
            cap = _cap(_tien_cum(p)) | {c for x in _la(p) for c in _cap(x)}
            return ten, cap
        for p in _ds(data.get("DanhSachPhi")):
            if isinstance(p, dict):
                ten, cap = phi(p)
                if ten:
                    out.append((ten, {"tien"}, cap, ""))
        for c in _ds(data.get("CachThucThucHien")):
            if not isinstance(c, dict):
                continue
            nop = _n(_NOP.get(str(c.get("HinhThucNop", "")).strip(), c.get("HinhThucNop")))
            cap = _cap(_han(c)) | {x for t in _la(c) for x in _cap(t)}
            loai = {"thoi_gian"}
            for p in _ds(c.get("DanhSachPhi")):
                if isinstance(p, dict):
                    ten, cp = phi(p)
                    cap |= cp
                    loai.add("tien")
                    if ten:
                        out.append((ten, {"tien"}, cp, ""))
            if nop:
                # Hai dòng cùng hình thức nộp (ví dụ hai “Trực tiếp” cho hai trường hợp) được
                # phân biệt bằng phần mô tả đi kèm, nếu dòng trả lời có chép phần mô tả đó.
                out.append((nop, loai, cap, _n(c.get("MoTa"))))
    return out


def _sai_chu_the(dong_n: str, thuc_the) -> List[str]:
    """Cặp số–đơn vị trong dòng không thuộc chủ thể mà dòng đang nhắc tên.

    Sửa 20/10 bản 3 (F06): một dòng có nhiều vế (ngăn bởi “;”, dấu chấm cuối câu, và từ 21/10 bản 2
    cả dấu phẩy và chữ “và”) được xét
    TỪNG VẾ. Trước đây số của mọi chủ thể cùng có mặt trong dòng bị gộp chung, nên
    “Tờ khai Alpha cần 2 bản chính; Văn bản Beta có liên quan.” (2 bản là của Beta) lọt qua.
    Vế không nhắc tên chủ thể nào thì xét theo các chủ thể của cả dòng như cũ."""
    # Điểm ngắt vế: “;” hoặc dấu chấm + khoảng trắng, trừ khi nằm BÊN TRONG tên một chủ thể
    # (tên giấy tờ có thể chứa “;” hoặc “a. …”).
    phu = []
    for x in thuc_the:
        if x[0]:
            phu += [(m.start(), m.end()) for m in re.finditer(re.escape(x[0]), dong_n)]
    cat, dau = [], 0
    for m in re.finditer(r";|\.\s|,\s|\svà\s", dong_n):     # 21/10 bản 2: thêm dấu phẩy và chữ “và”
        if not any(a <= m.start() < b for a, b in phu):
            cat.append(dong_n[dau:m.start()])
            dau = m.end()
    cat.append(dong_n[dau:])
    ve = [v for v in cat if v.strip()]
    if len(ve) <= 1:
        return _sai_mot_ve(dong_n, dong_n, thuc_the, dong_n)
    out: List[str] = []
    for v in ve:
        co_ten = any(x[0] and x[0] in v for x in thuc_the)
        for x in _sai_mot_ve(v if co_ten else dong_n, v, thuc_the, dong_n):
            if x not in out:
                out.append(x)
    return out


def _sai_mot_ve(vung_ten: str, dong_n: str, thuc_the, ca_dong: str) -> List[str]:
    """Các cặp số–đơn vị của `dong_n` không thuộc chủ thể được nhắc tên trong `vung_ten`.
    Chủ thể trùng tên được phân biệt bằng mô tả chép trong CẢ DÒNG (`ca_dong`)."""
    gap = [x for x in thuc_the if x[0] and x[0] in vung_ten]
    ten_gap = {x[0] for x in gap}
    gap = [x for x in gap if not any(x[0] != t and x[0] in t for t in ten_gap)]
    # Trùng tên: nếu dòng chép đúng mô tả của một (vài) chủ thể thì chỉ giữ các chủ thể đó.
    for ten in {x[0] for x in gap}:
        cung = [x for x in gap if x[0] == ten]
        khop_mo_ta = [x for x in cung if x[3] and x[3] in ca_dong]
        if len(cung) > 1 and khop_mo_ta:
            gap = [x for x in gap if x[0] != ten] + khop_mo_ta
    if not gap:
        return []
    duoc, quy_dinh = set(), set()
    for ten, loai, cap, _ in gap:
        quy_dinh |= loai
        duoc |= cap | _cap(ten)
    return [f"{a} {b}" for a, b in sorted(_cap(dong_n)) if _loai(b) in quy_dinh and (a, b) not in duoc]


def _la(v) -> List[str]:
    """Mọi chuỗi lá khác rỗng trong một cấu trúc bất kỳ."""
    if isinstance(v, dict):
        return [x for k in v for x in _la(v[k])]
    if isinstance(v, list):
        return [x for i in v for x in _la(i)]
    t = _n(v)
    return [t] if t else []


class DuKien:
    """Một dữ kiện mong đợi: mô tả + điều kiện một DÒNG trả lời phải thỏa."""

    def __init__(self, mo_ta: str, *chuoi: str, so: str = "", dem: bool = True, cum=()):
        self.mo_ta = mo_ta
        # cụm phải xuất hiện nguyên vẹn (bản chặt): “3 ngày làm việc”, “125.000 đồng”, “1 bản chính”
        self.chuoi = [_n(c) for c in list(chuoi) + list(cum) if _n(c)]
        self.so = [x.lstrip("0") or "0" for x in so.split("|") if x]
        # dem=True: mỗi dòng trả lời chỉ dùng cho MỘT dữ kiện (đếm đúng số lần,
        # ví dụ hai giấy tờ trùng tên phải là hai dòng). dem=False: dữ kiện
        # dạng liệt kê, nhiều dữ kiện có thể nằm chung một dòng.
        self.dem = dem

    def khop(self, dong_n: str, dong_so: set) -> bool:
        return all(c in dong_n for c in self.chuoi) and all(x in dong_so for x in self.so)


def du_kien_mong_doi(data: Dict, y: str) -> List[DuKien]:
    """Liệt kê dữ kiện của mục `y` đọc thẳng từ JSON gốc."""
    out: List[DuKien] = []
    if y == "ho_so":
        for h in _ds(data.get("ThanhPhanHoSo")):
            if isinstance(h, dict):
                for g in _ds(h.get("DanhSachGiayTo")):
                    if isinstance(g, dict) and _n(g.get("TenGiayTo")):
                        bc, bs = _so(g.get("SoBanChinh")).lstrip("0"), _so(g.get("SoBanSao")).lstrip("0")
                        cum = ([f"{bc} bản chính"] if bc else []) + ([f"{bs} bản sao"] if bs else [])
                        out.append(DuKien(f"giấy tờ: {g['TenGiayTo'][:60]}", g["TenGiayTo"], cum=cum))
    elif y == "le_phi":
        def phi(p, han=None, cum_han=(), nop=""):
            if not isinstance(p, dict):
                for t in _la(p):
                    out.append(DuKien(f"phí (dạng lạ): {t[:60]}", t))
                return
            ten, tien = _n(p.get("TenPhi")), _so(p.get("SoTien"))
            if not (ten or tien or _n(p.get("CachTinhPhi")) or _n(p.get("ThoiDiemThu"))):
                return
            so = "|".join(x for x in [tien, han] if x)
            thu = str(p.get("ThoiDiemThu") or "").strip()
            cum = [_tien_cum(p), _THU.get(thu, thu), _n(p.get("CachTinhPhi")), nop] + list(cum_han)
            out.append(DuKien(f"phí: {ten[:50] or '(không tên)'} {tien}" + (f" / thời hạn {han}" if han else ""),
                              ten, so=so, cum=cum))
        for p in _ds(data.get("DanhSachPhi")):
            phi(p)
        for c in _ds(data.get("CachThucThucHien")):
            if isinstance(c, dict):
                nop = _NOP.get(str(c.get("HinhThucNop", "")).strip(), c.get("HinhThucNop")) or ""
                for p in _ds(c.get("DanhSachPhi")):
                    phi(p, _so(c.get("ThoiGianXuLy")), [_han(c)], _n(nop))
    elif y == "thoi_han":
        for c in _ds(data.get("CachThucThucHien")):
            if isinstance(c, dict):
                nop = _NOP.get(str(c.get("HinhThucNop", "")).strip(), c.get("HinhThucNop"))
                out.append(DuKien(f"thời hạn: {nop} {c.get('ThoiGianXuLy')}", nop or "", c.get("MoTa") or "",
                                  so=_so(c.get("ThoiGianXuLy")), cum=[_han(c)]))
            else:
                for t in _la(c):
                    out.append(DuKien(f"cách thức (dạng lạ): {t[:60]}", t))
    elif y == "trinh_tu":
        # Một bước = một dữ kiện: tên bước và mô tả của CÙNG bước phải nằm cùng một dòng
        for i, b in enumerate(_ds(data.get("CacBuocThucHien")), 1):
            la = _la(b)
            if la:
                out.append(DuKien(f"bước {i}: {la[0][:60]}", *la))
    elif y == "dieu_kien":
        for t in _la(data.get("YeuCauDieuKien")):
            out.append(DuKien(f"điều kiện: {t[:60]}", t))
    elif y == "noi_nop":
        for t in _la(data.get("DiaChiTiepNhanHoSo")):
            out.append(DuKien(f"địa chỉ: {t[:60]}", t))
        for k, ten in _CAP.items():
            if _n(data.get(k)) == "true":
                out.append(DuKien(f"cấp thực hiện: {ten}", ten, dem=False))
        da = set()
        for c in _ds(data.get("CachThucThucHien")):
            if isinstance(c, dict):
                nop = _NOP.get(str(c.get("HinhThucNop", "")).strip(), c.get("HinhThucNop"))
                if _n(nop) and _n(nop) not in da:
                    da.add(_n(nop))
                    out.append(DuKien(f"hình thức nộp: {nop}", nop, dem=False))
    else:
        khoa, con = {"ket_qua": ("DanhSachKetQua", "TenKetQua"), "can_cu": ("DanhSachCanCuPhapLy", "TenCanCu"),
                     "doi_tuong": ("DoiTuongThucHien", "TenDoiTuong")}[y]
        for x in _ds(data.get(khoa)):
            if isinstance(x, dict) and _n(x.get(con)):
                out.append(DuKien(f"{y}: {x[con][:60]}", x[con]))
            else:
                for t in _la(x):
                    out.append(DuKien(f"{y}: {t[:60]}", t))
    return out


TRUONG = {"ho_so": ["ThanhPhanHoSo"], "le_phi": ["DanhSachPhi", "CachThucThucHien"],
          "thoi_han": ["CachThucThucHien"], "trinh_tu": ["CacBuocThucHien"], "dieu_kien": ["YeuCauDieuKien"],
          "noi_nop": ["DiaChiTiepNhanHoSo", "CachThucThucHien"], "ket_qua": ["DanhSachKetQua"],
          "can_cu": ["DanhSachCanCuPhapLy"], "doi_tuong": ["DoiTuongThucHien"]}


def doi_chieu(data: Dict, y: str, dong: List[str]) -> Dict:
    """
    So các dòng trả lời của một mục với nguồn. Ghép dữ kiện–dòng theo kiểu
    "mỗi dòng dùng cho tối đa một dữ kiện" để đếm đúng số lần xuất hiện.
    """
    dk = du_kien_mong_doi(data, y)
    # Mỗi dòng: chữ đã chuẩn hóa + tập các số trong dòng (bỏ dấu phân cách hàng nghìn)
    dn = [(_n(x), {(_so(t).lstrip("0") or "0") for t in re.findall(r"\d[\d.,]*", x)}) for x in dong]
    da_dung = [False] * len(dn)
    thieu = []
    for d in dk:
        for i, (t, s) in enumerate(dn):
            if (not d.dem or not da_dung[i]) and d.khop(t, s):
                if d.dem:
                    da_dung[i] = True
                break
        else:
            thieu.append(d.mo_ta)
    # Căn cứ: mỗi dòng phải chứa ít nhất một chuỗi lá (>= 3 ký tự) của phần nguồn
    la = [x for k in TRUONG[y] for x in _la(data.get(k)) if len(x) >= 3]
    la += [_n(t) for t in _NOP.values()] if y in ("noi_nop", "thoi_han", "le_phi") else []
    la += [_n(t) for t in _CAP.values()] if y == "noi_nop" else []
    khong_can_cu = [dong[i] for i, (t, _) in enumerate(dn)
                    if not t.startswith("trường hợp") and not any(x in t for x in la)]
    # Bản chặt: mọi cặp số–đơn vị trong câu trả lời phải có trong nguồn của mục
    # (từ trường có cấu trúc, hoặc nằm sẵn trong một chuỗi mô tả của nguồn).
    nguon_cap: Set[Tuple[str, str]] = set()
    for x in la:
        nguon_cap |= _cap(x)
    for k in TRUONG[y]:
        for c in _ds(data.get(k)):
            if not isinstance(c, dict):
                continue
            if c.get("ThoiGianXuLy") not in (None, ""):
                nguon_cap |= _cap(_han(c))
            for p in _ds(c.get("DanhSachPhi")) + ([c] if "SoTien" in c else []):
                if isinstance(p, dict):
                    nguon_cap |= _cap(_tien_cum(p))
            for h in ([c] if "DanhSachGiayTo" in c else []):
                for g in _ds(h.get("DanhSachGiayTo")):
                    if isinstance(g, dict):
                        for f, ten in (("SoBanChinh", "bản chính"), ("SoBanSao", "bản sao")):
                            so = _so(g.get(f)).lstrip("0")
                            if so:
                                nguon_cap.add((so, ten))
    sai_lech = []
    thuc_the = _thuc_the(data, y)
    for i, (t, _) in enumerate(dn):
        la_cap = _cap(t) - nguon_cap
        if la_cap:
            sai_lech.append(f"{dong[i][:120]}  ⟵ không có trong nguồn: "
                            + ", ".join(f"{a} {b}" for a, b in sorted(la_cap)))
            continue
        sai_ct = _sai_chu_the(t, thuc_the)
        if sai_ct:
            sai_lech.append(f"{dong[i][:120]}  ⟵ có trong nguồn nhưng của chủ thể khác: " + ", ".join(sai_ct))
    return {"phien_ban": PHIEN_BAN, "so_du_kien": len(dk), "co_trong_tra_loi": len(dk) - len(thieu),
            "thieu": thieu, "so_dong": len(dong), "dong_khong_can_cu": khong_can_cu,
            "dong_sai_lech": sai_lech}
