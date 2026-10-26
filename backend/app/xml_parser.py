"""
Chuyển dữ liệu XML từ API Cổng Dịch vụ công sang JSON.

NGUYÊN TẮC: TRUNG THỰC TUYỆT ĐỐI.
  - Giữ nguyên tên trường như API đặt (MaThuTucHanhChinh, TenThuTuc, ...).
  - Giữ nguyên giá trị như API trả về (DIRECT, WORKING_DAY, ACTIVE, 125000...).
  - KHÔNG dịch, KHÔNG gộp dòng trùng, KHÔNG bỏ trường, KHÔNG tự sinh thêm dữ liệu.
  - Thẻ lặp lại nhiều lần -> gom thành danh sách, đúng thứ tự API trả về.
"""
import re
from xml.etree import ElementTree as ET

NS = re.compile(r"\{.*?\}")

# Các thẻ thuộc lớp vỏ phản hồi / chữ ký số, không phải dữ liệu thủ tục
VO_BOC = {
    "ResponseEnvelope", "Content", "MessageId", "RefMessageId", "ErrorCode",
    "Message", "Data", "RequestId", "ReceivedAt", "r", "error_code",
    "TongSoBanGhi", "LastId", "Result", "result",
    "Signature", "SignedInfo", "SignatureValue", "CanonicalizationMethod",
    "SignatureMethod", "Reference", "Transforms", "Transform",
    "DigestMethod", "DigestValue", "KeyInfo", "X509Data", "X509Certificate", "Object",
}


def _tag(el):
    return NS.sub("", el.tag)


def to_value(el):
    """
    Chuyển một nút XML thành giá trị Python, giữ nguyên cấu trúc gốc.
      - Nút không có con  -> chuỗi văn bản (nguyên bản)
      - Nút có con        -> dict {tên_thẻ: giá_trị}
      - Thẻ xuất hiện nhiều lần -> danh sách
    """
    children = list(el)
    if not children:
        return (el.text or "").strip()

    out = {}
    for c in children:
        name = _tag(c)
        val = to_value(c)
        if name in out:
            if not isinstance(out[name], list):
                out[name] = [out[name]]
            out[name].append(val)
        else:
            out[name] = val
    return out


def _first_text(d, key):
    """Lấy giá trị văn bản đầu tiên của một khóa (dùng cho cột lọc/tra cứu)."""
    v = d.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        return None
    return v or None


def _nested_text(d, parent, child):
    """Lấy giá trị con bên trong một khóa cha, ví dụ CoQuanBanHanh > TenCoQuanBanHanh."""
    p = d.get(parent)
    if isinstance(p, list):
        p = p[0] if p else None
    if isinstance(p, dict):
        return _first_text(p, child)
    return None


def _gom_van_ban(value, acc):
    """Gom toàn bộ văn bản trong cấu trúc để phục vụ tra cứu toàn văn."""
    if isinstance(value, str):
        if value:
            acc.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            _gom_van_ban(v, acc)
    elif isinstance(value, list):
        for v in value:
            _gom_van_ban(v, acc)


def parse_procedures(xml_text, agency_name=None):
    """
    Đọc XML -> danh sách bản ghi để lưu vào cơ sở dữ liệu.

    Mỗi bản ghi gồm:
      - Vài cột phẳng CHỈ để lọc và tra cứu nhanh, lấy nguyên giá trị từ API.
      - Cột `data`: toàn bộ dữ liệu gốc, giữ nguyên cấu trúc và giá trị.

    Tham số agency_name được giữ lại cho tương thích nhưng KHÔNG dùng để
    ghi đè dữ liệu API (trước đây có ghi đè, nay đã bỏ để bảo đảm trung thực).
    """
    xml_text = xml_text.lstrip("\ufeff").strip()
    root = ET.fromstring(xml_text)

    records = []
    for el in root.iter():
        tags = [_tag(c) for c in el]
        if "MaThuTucHanhChinh" not in tags or "TenThuTuc" not in tags:
            continue

        data = to_value(el)
        # loại các thẻ vỏ bọc lỡ lọt vào (không ảnh hưởng dữ liệu thủ tục)
        data = {k: v for k, v in data.items() if k not in VO_BOC}

        ten = _first_text(data, "TenThuTuc")
        if not ten:
            continue

        acc = []
        _gom_van_ban(data, acc)

        records.append({
            "procedure_code": _first_text(data, "MaThuTucHanhChinh"),
            "title": ten,
            # lấy NGUYÊN giá trị API trả về, không thay bằng tên cứng
            "agency": _nested_text(data, "CoQuanBanHanh", "TenCoQuanBanHanh"),
            "category": _nested_text(data, "LinhVuc", "TenLinhVuc"),
            "search_text": " ".join(acc),
            "status": "published",
            "data": data,
        })
    return records


def extract_last_id(xml_text):
    m = re.search(r"<LastId>(.*?)</LastId>", xml_text, re.DOTALL)
    return m.group(1).strip() if m else None


def extract_total(xml_text):
    m = re.search(r"<TongSoBanGhi>(.*?)</TongSoBanGhi>", xml_text, re.DOTALL)
    return int(m.group(1).strip()) if m else None
