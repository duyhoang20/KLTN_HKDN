"""Che thông tin cá nhân trong câu người dân gõ (tách khỏi main.py ngày 20/10 bản 3 để
dùng chung cho nhật ký và cho lớp mô hình ngôn ngữ).

Chỉ che theo khuôn: cụm từ 9 chữ số trở lên (căn cước, điện thoại) và email. Tên, địa chỉ
người dân tự gõ KHÔNG được che. Vì vậy không mô tả nhật ký là “đã ẩn danh hoàn toàn”.
"""
import re

# Sửa 14/10 (bản 2): người dân có thể gõ số căn cước, số điện thoại, email vào câu hỏi. Nhật ký
# chỉ cần nội dung hỏi để phân tích nhu cầu, nên các chuỗi này được che TRƯỚC khi lưu
# (dãy từ 9 chữ số trở lên, kể cả có dấu cách/chấm/gạch giữa; địa chỉ email). Mã thủ tục
# dạng 1.000894 (7 chữ số) và số tiền thông thường không bị che.
# Cụm chữ số có thể kèm dấu cộng, ngoặc, dấu chấm, gạch nối và nhiều dấu cách:
# (0912) 345 678 | +84 912 345 678 | 0912  345  678 | 001099012345 (sửa 15/10).
_RE_CUM_SO = re.compile(r"(?:\+\s*)?\(?\+?\d(?:[ \t().\-]{0,3}\d)+\)?")
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Số tiền như "1.250.000.000 đồng" có nhiều chữ số nhưng không phải dữ liệu cá nhân.
_RE_SAU_LA_TIEN = re.compile(r"\s*(?:đồng|đ\b|vnđ|vnd|usd)", re.IGNORECASE)
SO_CHU_SO_TOI_THIEU = 9   # mã thủ tục (1.000894) có 7 chữ số nên được giữ


def che_thong_tin_ca_nhan(s: str) -> str:
    """Che số căn cước, số điện thoại, email trong câu người dân gõ trước khi ghi nhật ký.
    Chỉ che theo khuôn (cụm từ 9 chữ số, email); không bảo đảm che mọi thông tin nhận diện."""
    # Sửa 20/10 bản 3 (F12): gộp mọi chuỗi khoảng trắng thành một dấu cách trước khi che,
    # nên “0912    345 678” (nhiều dấu cách) cũng bị che.
    s = re.sub(r"\s+", " ", s or "").strip()
    s = _RE_EMAIL.sub("[đã ẩn email]", s)

    def thay(m: re.Match) -> str:
        if sum(ch.isdigit() for ch in m.group(0)) < SO_CHU_SO_TOI_THIEU:
            return m.group(0)
        if _RE_SAU_LA_TIEN.match(s, m.end()):
            return m.group(0)
        return "[đã ẩn số]"

    return _RE_CUM_SO.sub(thay, s)


