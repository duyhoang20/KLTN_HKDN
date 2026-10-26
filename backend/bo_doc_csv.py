"""Bộ đọc CSV NGHIÊM NGẶT dùng chung cho các bộ đo (bổ sung 09/10/2026).

Vì sao cần: bộ đề được sửa bằng Excel. Nếu bộ đọc dễ dãi thì một lỗi định dạng
có thể làm một câu bị bỏ khỏi mẫu số, hoặc nhãn bị ghi đè, mà KHÔNG có cảnh
báo — chỉ số khi đó đẹp lên giả tạo. Vì vậy mọi lỗi dưới đây đều làm bộ đo
DỪNG và liệt kê đủ, kèm số dòng vật lý trong file (đúng số dòng Excel/Notepad
hiển thị, kể cả khi một ô có xuống dòng bên trong):

  - file không phải UTF-8;
  - dấu nháy kép không đóng hoặc đặt sai chỗ;
  - tiêu đề cột rỗng, tiêu đề trùng (kể cả khi chỉ khác khoảng trắng hay hoa/thường);
  - thiếu cột bắt buộc;
  - dòng THIẾU ô so với tiêu đề;
  - dòng THỪA ô so với tiêu đề; dữ liệu nằm ở cột không có tên (các cột trống ở
    cuối mà Excel đôi khi thêm vào thì được chấp nhận nếu mọi ô của chúng trống).

Bộ đọc này chỉ kiểm tra CẤU TRÚC bảng. Kiểm tra ý nghĩa (mã thủ tục có trong
kho, loại câu hợp lệ, nhãn ngoài phạm vi...) do từng bộ đo tự làm.
"""
import csv
import io
from pathlib import Path


class LoiBoDe(Exception):
    """Bộ đề không hợp lệ; thuộc tính .loi là danh sách thông báo."""

    def __init__(self, loi):
        super().__init__("\n".join(loi))
        self.loi = loi


def doc_van_ban(path):
    """Đọc file; báo rõ khi Excel lưu sai bảng mã."""
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise LoiBoDe([
            "File không ở dạng UTF-8 (thường do Excel lưu kiểu 'CSV (Comma delimited)').",
            "Trong Excel chọn File > Save As > 'CSV UTF-8 (Comma delimited) (*.csv)' rồi chạy lại.",
        ])


def _vi_tri(bat_dau, ket_thuc):
    return f"Dòng {bat_dau}" if bat_dau == ket_thuc else f"Dòng {bat_dau}–{ket_thuc}"


def doc_bang(path, cot_bat_buoc):
    """
    Đọc CSV thành [(vị trí, {cột: giá trị đã strip})] và văn bản gốc.

    `vị trí` là chuỗi "Dòng 12" hoặc "Dòng 12–14" (ô có xuống dòng). Dòng trống
    hoàn toàn bị bỏ qua. Lỗi cấu trúc -> LoiBoDe với đầy đủ danh sách lỗi.
    """
    text = doc_van_ban(path)
    if not text.strip():
        raise LoiBoDe(["File bộ đề trống, không có dòng tiêu đề."])
    dau = text.split("\n", 1)[0]
    # Excel đặt vùng Việt Nam thường lưu CSV bằng dấu chấm phẩy.
    phan_cach = ";" if dau.count(";") > dau.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=phan_cach, strict=True)

    loi, ban_ghi = [], []
    dong_truoc = 0
    try:
        tieu_de = next(reader)
        dong_truoc = reader.line_num
    except csv.Error as e:
        raise LoiBoDe([f"Dòng 1: lỗi định dạng CSV ở dòng tiêu đề ({e})."])
    cot = [c.strip() for c in tieu_de]
    # Excel đôi khi ghi thêm các cột trống ở CUỐI (ô từng có dữ liệu rồi bị xóa).
    # Chấp nhận các cột cuối không tên đó với điều kiện mọi ô của chúng trống.
    n = len(cot)
    while n and not cot[n - 1]:
        n -= 1
    for i, c in enumerate(cot[:n], 1):
        if not c:
            loi.append(f"Dòng 1: cột thứ {i} không có tên. Xóa cột trống này trong Excel rồi lưu lại.")
    thay = {}
    for i, c in enumerate(cot[:n], 1):
        k = c.lower()
        if k and k in thay:
            loi.append(f"Dòng 1: tên cột '{c}' (cột {i}) trùng với cột {thay[k]}; "
                       "giá trị của một trong hai cột sẽ bị ghi đè nên bộ đo dừng.")
        thay.setdefault(k, i)
    thieu = [c for c in cot_bat_buoc if c not in cot]
    if thieu:
        loi.append(f"Dòng 1: thiếu cột {', '.join(thieu)}. Tiêu đề đọc được: {', '.join(cot)}")
    if loi:
        raise LoiBoDe(loi)

    tong_cot = len(cot)
    while True:
        try:
            hang = next(reader)
        except StopIteration:
            break
        except csv.Error as e:
            loi.append(f"Dòng {dong_truoc + 1}: lỗi định dạng CSV ({e}). "
                       "Thường do dấu nháy kép (\") không đóng hoặc đặt giữa ô.")
            break      # sau lỗi nháy, vị trí đọc không còn tin cậy
        bat_dau, dong_truoc = dong_truoc + 1, reader.line_num
        vt = _vi_tri(bat_dau, dong_truoc)
        if not any(x.strip() for x in hang):
            continue                       # dòng trống hoàn toàn
        if len(hang) < n:
            loi.append(f"{vt}: thiếu ô — có {len(hang)} ô trong khi tiêu đề có {n} cột có tên. "
                       "Có thể một ô bị xóa mất dấu phân cách.")
            continue
        if len(hang) > tong_cot:
            loi.append(f"{vt}: thừa ô — có {len(hang)} ô trong khi tiêu đề có {tong_cot} cột. "
                       "Thường do dấu phẩy trong câu hỏi mà ô không được đặt trong nháy kép.")
            continue
        if any(x.strip() for x in hang[n:]):
            loi.append(f"{vt}: có dữ liệu ở cột không có tên tiêu đề "
                       f"({', '.join(repr(x) for x in hang[n:] if x.strip())}). "
                       "Thường do dấu phẩy trong câu hỏi mà ô không được đặt trong nháy kép.")
            continue
        ban_ghi.append((vt, {cot[i]: hang[i].strip() for i in range(n)}))
    if loi:
        raise LoiBoDe(loi)
    return ban_ghi, text
