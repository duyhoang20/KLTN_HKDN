"""
Tra cứu thủ tục hành chính — xây trên mô hình BM25.

VÌ SAO CHỌN BM25
    BM25 (Okapi BM25) là mô hình xếp hạng chuẩn trong lĩnh vực truy xuất thông
    tin, được dùng làm mặc định trong Elasticsearch, Lucene, Solr. Nó có cơ sở
    lý thuyết rõ ràng (mô hình xác suất) và ba thành phần:

      1. IDF   — từ càng hiếm trong kho dữ liệu càng mang nhiều thông tin.
                 "đăng ký" có ở hàng nghìn thủ tục nên gần như vô nghĩa,
                 "hộ khẩu" thì đặc trưng.
      2. Bão hòa tần suất (k1) — một từ lặp 10 lần không có nghĩa là liên quan
                 gấp 10 lần lặp 1 lần.
      3. Chuẩn hóa độ dài (b) — tiêu đề dài tự nhiên chứa nhiều từ hơn nên dễ
                 khớp hơn; phải trừ hao để không thiên vị tiêu đề dài.

    Tham số k1 = 1.5 và b = 0.75 là giá trị chuẩn được khuyến nghị trong tài
    liệu gốc và dùng rộng rãi, không phải do người viết tự chọn.

BA ĐIỀU CHỈNH CHO TIẾNG VIỆT

    a) Đơn vị đánh chỉ mục: âm tiết đơn VÀ cặp âm tiết liền nhau.
       Từ tiếng Việt thường gồm nhiều âm tiết. Nếu chỉ dùng âm tiết rời thì
       "vi phạm" khớp trúng "phạm vi". Cặp âm tiết giữ được thứ tự.

    b) Độ gắn kết của cặp âm tiết.
       "hộ khẩu" là một từ thật: âm "khẩu" hầu như chỉ xuất hiện ngay sau "hộ".
       "ký hộ" chỉ là chỗ giáp ranh giữa "đăng ký" và "hộ kinh doanh"; hai âm
       tiết này vốn xuất hiện độc lập khắp nơi. Đo bằng tỉ lệ đồng xuất hiện,
       cụm ghép tình cờ bị hạ trọng số.

    c) Nhận biết dấu thanh.
       Bỏ dấu cho dễ gõ thì "hỗ" và "hộ" đều thành "ho", khiến "đăng ký hỗ trợ"
       khớp nhầm "đăng ký hộ khẩu". Nếu người dùng có gõ dấu thì phần khớp
       đúng dấu được tính trọn, phần chỉ khớp khi bỏ dấu bị hạ điểm.

BỔ SUNG NGÀY 24/09/2026
    Tăng điểm 30% nếu toàn bộ truy vấn gồm ít nhất hai âm tiết xuất hiện
    liên tiếp trong tiêu đề, có xét ranh giới âm tiết. Truy vấn có dấu phải
    khớp bản có dấu; truy vấn không dấu khớp bản bỏ dấu. Đây chỉ là một tín
    hiệu xếp hạng bổ sung; ứng viên không khớp cả cụm vẫn được chấm BM25.
    Không dùng toàn văn, không gộp/xóa bản ghi trùng tên.

SỬA NGÀY 29/09/2026
    Hoàn tác bản sửa mẫu số phần trăm ngày 28/09 (làm truy vấn ngoài phạm vi
    nhận kết quả sai tới 100%). Sửa lỗi Unicode: norm_dau() đưa về NFC trước
    khi lọc ký tự. Trước đó chữ dạng NFD bị vỡ âm tiết ở nhánh có dấu, cả
    trong truy vấn lẫn 134 tiêu đề của kho. Công thức, hệ số, ngưỡng giữ nguyên.

PHẠM VI TRA CỨU
    Chỉ xét TIÊU ĐỀ + LĨNH VỰC, không xét toàn văn. Thân bài chứa cả danh mục
    giấy tờ phải nộp, nên rất nhiều thủ tục có câu "bản sao đăng ký hộ khẩu"
    trong hồ sơ. Thủ tục YÊU CẦU NỘP hộ khẩu khác hẳn thủ tục VỀ hộ khẩu.
"""
import math
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Set, Tuple

from .models import GuidanceDocument
from .hieu_truy_van import phan_tich

# --- Tham số BM25, dùng giá trị chuẩn trong tài liệu gốc ---
K1 = 1.5     # mức bão hòa tần suất
B = 0.75     # mức chuẩn hóa theo độ dài

# Cặp âm tiết là bằng chứng mạnh hơn âm tiết rời nên được nhân thêm trọng số
TRONG_SO_CAP = 2.5
# Cụm ghép tình cờ (gắn kết thấp) chỉ còn phần nhỏ trọng số
SAN_GAN_KET = 0.25
# Phần chỉ khớp khi đã bỏ dấu (có thể nhầm hộ/hỗ) tính bằng tỉ lệ này
HE_SO_BO_DAU = 0.4

# Khớp trọn cụm liên tiếp trong TIÊU ĐỀ: nhân 1,3 điểm sau điều chỉnh dấu.
# Chọn trên kho thật với danh_gia.py ABC-20260924-1; các mức đã thử:
# 1,15; 1,3; 1,5. Mức 1,3 đạt cùng A/B với 1,5 và được chọn vì nhỏ hơn.
# Đây là hệ số thực nghiệm, không phải tham số chuẩn của BM25.
HE_SO_CUM_LIEN_TIEP = 1.3

STOPWORDS: Set[str] = {
    "va", "hoac", "cua", "cho", "la", "co", "khong", "gi", "the", "nao",
    "duoc", "voi", "cac", "nhung", "mot", "de", "khi", "tai", "trong",
    "ve", "den", "tu", "theo", "doi", "su", "viec",
}


# ===================== Chuẩn hóa văn bản =====================

def _bo_dau(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def norm_dau(text: str) -> str:
    """Chữ thường, bỏ ký tự đặc biệt, GIỮ dấu.

    Đưa về NFC trước khi lọc ký tự (sửa 29/09/2026). Ở dạng NFD, dấu nằm
    thành ký tự tổ hợp riêng, không thuộc lớp à-ỹ, nên bị thay bằng khoảng
    trắng và làm vỡ âm tiết. Nhánh bỏ dấu (normalize) vốn đã đúng với NFD.
    """
    text = unicodedata.normalize("NFC", (text or "").lower())
    text = re.sub(r"[^0-9a-zà-ỹđ\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(text: str) -> str:
    """Chữ thường, BỎ dấu, bỏ ký tự đặc biệt."""
    text = _bo_dau((text or "").lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tach_tu(text: str) -> List[str]:
    """
    Sinh đơn vị đánh chỉ mục từ một chuỗi: âm tiết đơn + cặp âm tiết liền nhau.
    Cặp được đánh dấu bằng khoảng trắng bên trong để phân biệt với âm tiết đơn.
    """
    syl = [s for s in text.split() if s]
    don = [s for s in syl if len(s) >= 2 and s not in STOPWORDS]
    cap = [f"{syl[i]} {syl[i+1]}" for i in range(len(syl) - 1)]
    return don + cap


def la_cap(term: str) -> bool:
    return " " in term


# ===================== Chỉ mục toàn kho =====================

_IDX: Dict = {"n": -1}


def xay_chi_muc(docs: List[GuidanceDocument]) -> None:
    """
    Tính sẵn MỘT LẦN toàn bộ số liệu cần cho tra cứu:

      - Tách từ sẵn cho từng thủ tục (không phải tách lại ở mỗi truy vấn).
      - Tần suất tài liệu của mỗi đơn vị, độ dài trung bình.
      - CHỈ MỤC NGƯỢC: từ mỗi đơn vị -> danh sách thủ tục có chứa nó.

    Chỉ mục ngược là điểm mấu chốt về tốc độ: thay vì chấm điểm cả 9.451 thủ
    tục cho mỗi truy vấn, hệ thống chỉ xét những thủ tục thật sự có chứa ít
    nhất một từ khóa — thường chỉ vài trăm.
    """
    df: Counter = Counter()
    df_syl: Counter = Counter()
    postings: Dict[str, set] = {}
    tf_doc: Dict[int, Counter] = {}
    tf_doc_dau: Dict[int, Counter] = {}
    do_dai: Dict[int, int] = {}
    tong_dai = 0
    tieu_de = {}
    tieu_de_dau = {}

    for d in docs:
        tieu_de[d.id] = " " + normalize(d.title or "") + " "
        tieu_de_dau[d.id] = " " + norm_dau(d.title or "") + " "
        vb = normalize(f"{d.title or ''} {d.category or ''}")
        terms = tach_tu(vb)
        tf_doc[d.id] = Counter(terms)
        do_dai[d.id] = len(terms)
        tong_dai += len(terms)

        tap = set(terms)
        df.update(tap)
        df_syl.update(set(vb.split()))
        for t in tap:
            postings.setdefault(t, set()).add(d.id)

        # bản có dấu, phục vụ phân biệt hộ / hỗ
        tf_doc_dau[d.id] = Counter(tach_tu(norm_dau(f"{d.title or ''} {d.category or ''}")))

    n = max(1, len(docs))
    _IDX.update({
        "n": len(docs),
        "tieu_de": tieu_de,
        "tieu_de_dau": tieu_de_dau,
        "df": df,
        "df_syl": df_syl,
        "postings": postings,
        "tf": tf_doc,
        "tf_dau": tf_doc_dau,
        "len": do_dai,
        "dai_tb": (tong_dai / n) or 1.0,
    })


def _idf(term: str) -> float:
    """
    IDF theo công thức BM25 (dạng có làm mượt).
    Chỉ mục xây bằng chữ không dấu nên phải quy về không dấu trước khi tra,
    nếu không mọi đơn vị có dấu sẽ bị coi là cực hiếm và chấm điểm tối đa.
    """
    n = _IDX["n"] or 1
    df = _IDX["df"].get(normalize(term), 0)
    return math.log(1 + (n - df + 0.5) / (df + 0.5))


def _gan_ket(cap: str) -> float:
    """
    Độ gắn kết của một cặp âm tiết: đây là từ thật hay chỉ tình cờ đứng cạnh?

    Tính bằng tỉ lệ giữa số tài liệu chứa cả cặp và số tài liệu chứa âm tiết
    hiếm hơn trong cặp. Với từ thật như "hộ khẩu", âm "khẩu" gần như chỉ đi
    cùng "hộ" nên tỉ lệ cao. Với "ký hộ" thì cả hai âm tiết đều xuất hiện
    độc lập ở rất nhiều nơi nên tỉ lệ thấp.
    """
    cap = normalize(cap)
    df_cap = _IDX["df"].get(cap, 0)
    if not df_cap:
        return 1.0
    a, b = cap.split(" ", 1)
    ds = _IDX["df_syl"]
    it_nhat = min(ds.get(a, df_cap), ds.get(b, df_cap)) or df_cap
    return max(0.0, min(1.0, df_cap / it_nhat))


def _trong_so(term: str) -> float:
    """Trọng số của một đơn vị truy vấn."""
    w = _idf(term)
    if la_cap(term):
        w *= TRONG_SO_CAP * (SAN_GAN_KET + (1 - SAN_GAN_KET) * _gan_ket(term))
    return w


# ===================== Chấm điểm BM25 =====================

def chuan_bi_truy_van(query: str) -> Dict:
    """
    Chuẩn bị truy vấn MỘT LẦN: tách từ và tính sẵn trọng số của từng đơn vị.
    Nhờ vậy khi chấm điểm hàng trăm thủ tục không phải tính lại trọng số.
    """
    kd, cd = normalize(query), norm_dau(query)
    terms, terms_dau = tach_tu(kd), tach_tu(cd)
    # Cố định thứ tự cộng số thực giữa các tiến trình Python. Duyệt set
    # trực tiếp có thể đảo các kết quả gần bằng điểm do sai số làm tròn.
    w = {t: _trong_so(t) for t in sorted(set(terms))}
    w_dau = {t: _trong_so(t) for t in sorted(set(terms_dau))}
    mau_chuan = (K1 + 1) / (1 + K1)
    return {
        "kd": kd,
        "cd": cd,
        "terms": terms,
        "terms_dau": terms_dau,
        "w": w,
        "w_dau": w_dau,
        "co_dau": kd != cd,
        "toi_da": sum(v * mau_chuan for v in w.values()) or 1.0,
    }


def _bm25_tf(w: Dict[str, float], tf: Counter, dl: int) -> float:
    """Điểm BM25, dùng bảng trọng số đã tính sẵn của truy vấn."""
    if not dl:
        return 0.0
    chuan = K1 * (1 - B + B * dl / _IDX["dai_tb"])
    diem = 0.0
    for t, wt in w.items():
        f = tf.get(t, 0)
        if f:
            diem += wt * (f * (K1 + 1)) / (f + chuan)
    return diem


def cham_diem(q: Dict, doc_id: int) -> Tuple[float, int]:
    tf = _IDX["tf"].get(doc_id)
    if not tf:
        return 0.0, 0
    dl = _IDX["len"].get(doc_id, 0)
    diem = _bm25_tf(q["w"], tf, dl)

    # Điều chỉnh theo dấu: phần khớp được khi bỏ dấu nhưng KHÔNG khớp đúng dấu
    # có nguy cơ nhầm lẫn (hộ / hỗ) nên bị hạ xuống.
    if q["co_dau"]:
        tf_d = _IDX["tf_dau"].get(doc_id, Counter())
        diem_dau = _bm25_tf(q["w_dau"], tf_d, dl)
        diem = diem_dau + HE_SO_BO_DAU * max(0.0, diem - diem_dau)

    # Cụm nhiều âm tiết xuất hiện LIÊN TIẾP trong tiêu đề là bằng chứng
    # mạnh hơn các âm tiết/cặp rải rác. Không loại ứng viên không khớp cụm.
    cum = q["cd"] if q["co_dau"] else q["kd"]
    bang_ten = _IDX["tieu_de_dau"] if q["co_dau"] else _IDX["tieu_de"]
    if " " in cum and f" {cum} " in bang_ten.get(doc_id, ""):
        diem *= HE_SO_CUM_LIEN_TIEP

    pt = round(100 * diem / q["toi_da"])
    return diem, max(1, min(100, pt))


# ===================== Giao diện tra cứu =====================

NGUONG_CHINH = 40      # phần trăm tối thiểu để coi là kết quả đáng tin
NGUONG_GOI_Y = 25      # phần trăm tối thiểu cho gợi ý gần đúng
SO_GOI_Y = 8           # số gợi ý tối đa khi không có kết quả đáng tin
TI_LE_SO_DAU = 0.55    # kết quả phải đạt ít nhất bằng ngần này so với kết quả đầu


def _search_don(query: str, docs: List[GuidanceDocument], limit: int = 60):
    """
    Tra cứu MỘT chuỗi truy vấn (thuật toán gốc, không đổi từ bản 29/09).

    Trả về [(tài liệu, điểm, phần trăm)] xếp theo độ liên quan giảm dần.

    Chỉ chấm điểm những thủ tục có chứa ít nhất một đơn vị của truy vấn,
    lấy từ chỉ mục ngược — không duyệt toàn bộ kho.

    Nếu không có kết quả nào vượt ngưỡng tin cậy, chỉ đưa vài gợi ý gần đúng
    nhất thay vì đổ ra hàng chục thủ tục không liên quan.
    """
    # Chỉ mục phải có trước, vì việc tính trọng số truy vấn cần số liệu toàn kho
    if _IDX.get("n") != len(docs):
        xay_chi_muc(docs)

    q = chuan_bi_truy_van(query)
    if not q["terms"]:
        return []

    # Lấy tập ứng viên từ chỉ mục ngược
    postings = _IDX["postings"]
    ung_vien: set = set()
    for t in set(q["terms"]):
        ids = postings.get(t)
        if ids:
            ung_vien |= ids
    if not ung_vien:
        return []

    by_id = {d.id: d for d in docs}
    chinh, goi_y = [], []
    for doc_id in ung_vien:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        diem, pt = cham_diem(q, doc_id)
        if pt >= NGUONG_CHINH:
            chinh.append((doc, diem, pt))
        elif pt >= NGUONG_GOI_Y:
            goi_y.append((doc, diem, pt))

    if chinh:
        # Cùng điểm: dùng ID làm thứ tự ổn định, không coi ID là độ liên quan.
        chinh.sort(key=lambda x: (-x[1], x[0].id))
        # Cắt bớt các kết quả yếu hơn hẳn so với kết quả đứng đầu. Nếu thủ tục
        # đầu bảng khớp rất sát mà một thủ tục khác chỉ khớp bằng nửa, thì thủ
        # tục đó nhiều khả năng không phải thứ người dùng cần.
        nguong = chinh[0][1] * TI_LE_SO_DAU
        chinh = [r for r in chinh if r[1] >= nguong]
        return chinh[:limit]
    goi_y.sort(key=lambda x: (-x[1], x[0].id))
    return goi_y[:SO_GOI_Y]


# ===================== Tra cứu có hiểu câu hỏi (08/10/2026) =====================

def _cham_bien_the(query: str) -> Dict[int, float]:
    """Chấm một biến thể: {id thủ tục: tỉ lệ khớp = điểm BM25 / điểm tối đa}."""
    q = chuan_bi_truy_van(query)
    if not q["terms"]:
        return {}
    postings = _IDX["postings"]
    ung_vien: set = set()
    for t in set(q["terms"]):
        ids = postings.get(t)
        if ids:
            ung_vien |= ids
    out = {}
    for doc_id in ung_vien:
        diem, _ = cham_diem(q, doc_id)
        if diem > 0:
            out[doc_id] = diem / q["toi_da"]
    return out


def search_chi_tiet(query: str, docs: List[GuidanceDocument], limit: int = 60):
    """
    Tra cứu có lớp hiểu câu hỏi. Trả về (kết quả, phân tích câu hỏi).

    - Câu không có từ đệm/từ đồng nghĩa: chỉ có một biến thể là câu gốc, đi
      đúng đường tính cũ (_search_don) nên kết quả giống hệt trước đây.
    - Câu có từ đệm/từ đồng nghĩa: chấm từng biến thể bằng cùng công thức, mỗi
      thủ tục nhận tỉ lệ khớp CAO NHẤT trong các biến thể. Ngưỡng 40%/25%,
      mức cắt 0,55 so với kết quả đầu và giới hạn 8 gợi ý giữ nguyên.
    """
    if _IDX.get("n") != len(docs):
        xay_chi_muc(docs)
    pt_cau = phan_tich(query)
    bien_the = pt_cau["bien_the"]
    if len(bien_the) <= 1:
        return _search_don(query, docs, limit), pt_cau

    tot: Dict[int, float] = {}
    for b in bien_the:
        for doc_id, ti_le in _cham_bien_the(b).items():
            if ti_le > tot.get(doc_id, 0.0):
                tot[doc_id] = ti_le
    by_id = {d.id: d for d in docs}
    chinh, goi_y = [], []
    for doc_id, ti_le in tot.items():
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        pt = max(1, min(100, round(100 * ti_le)))
        if pt >= NGUONG_CHINH:
            chinh.append((doc, ti_le, pt))
        elif pt >= NGUONG_GOI_Y:
            goi_y.append((doc, ti_le, pt))
    if chinh:
        chinh.sort(key=lambda x: (-x[1], x[0].id))
        nguong = chinh[0][1] * TI_LE_SO_DAU
        return [r for r in chinh if r[1] >= nguong][:limit], pt_cau
    goi_y.sort(key=lambda x: (-x[1], x[0].id))
    return goi_y[:SO_GOI_Y], pt_cau


def search(query: str, docs: List[GuidanceDocument], limit: int = 60):
    """Trả về [(tài liệu, điểm, phần trăm)] xếp theo độ liên quan giảm dần."""
    return search_chi_tiet(query, docs, limit)[0]


# ===================== Kiểu khớp hiển thị cho người dùng =====================

THU_TU_KIEU = {"trung_khop": 3, "nguyen_cum": 2, "du_tu": 1, "mot_phan": 0}


def kieu_khop(doc: GuidanceDocument, bien_the: List[str]) -> Dict:
    """
    Mô tả MINH BẠCH cách tên thủ tục khớp với truy vấn, theo đúng bốn mức mà
    nghiệp vụ yêu cầu. Chỉ để hiển thị và lọc, KHÔNG tham gia xếp hạng.

      trung_khop  tên thủ tục trùng hoàn toàn với truy vấn
      nguyen_cum  truy vấn xuất hiện nguyên cụm, liên tiếp trong tên thủ tục
      du_tu       tên thủ tục + lĩnh vực chứa đủ mọi từ khóa (không cần đúng thứ tự)
      mot_phan    chỉ chứa một phần; kèm tỉ lệ = số từ khóa khớp / số từ khóa hợp lệ

    Từ khóa hợp lệ = âm tiết của truy vấn, bỏ từ nối (STOPWORDS) và âm tiết 1 ký tự.
    Truy vấn có dấu thì so có dấu (hộ khác hỗ); không dấu thì so không dấu.
    Khi câu hỏi có nhiều biến thể (đã bỏ từ đệm / thay từ đồng nghĩa), lấy biến
    thể khớp tốt nhất.
    """
    ten_kd = " " + normalize(doc.title or "") + " "
    ten_cd = " " + norm_dau(doc.title or "") + " "
    tap_kd = set(normalize(f"{doc.title or ''} {doc.category or ''}").split())
    tap_cd = set(norm_dau(f"{doc.title or ''} {doc.category or ''}").split())
    tot = None
    for b in bien_the or []:
        kd, cd = normalize(b), norm_dau(b)
        co_dau = kd != cd
        am = (cd if co_dau else kd).split()
        tu = [s for s in dict.fromkeys(am) if len(s) >= 2 and _bo_dau(s) not in STOPWORDS]
        if not tu:
            continue
        tap = tap_cd if co_dau else tap_kd
        so_khop = sum(1 for s in tu if s in tap)
        cum, bang = (cd, ten_cd) if co_dau else (kd, ten_kd)
        if bang.strip() == cum:
            loai = "trung_khop"
        elif " " in cum and f" {cum} " in bang:
            loai = "nguyen_cum"
        elif so_khop == len(tu):
            loai = "du_tu"
        else:
            loai = "mot_phan"
        ung = (THU_TU_KIEU[loai], so_khop / len(tu), loai, so_khop, len(tu))
        if tot is None or ung[:2] > tot[:2]:
            tot = ung
    if tot is None:
        return {"kieu_khop": "mot_phan", "so_tu_khop": 0, "so_tu": 0, "ti_le_tu": 0}
    return {"kieu_khop": tot[2], "so_tu_khop": tot[3], "so_tu": tot[4],
            "ti_le_tu": round(100 * tot[3] / tot[4])}
