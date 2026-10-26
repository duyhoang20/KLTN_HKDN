"""Kiểm thử hồi quy cho bộ đọc bộ đề CSV (bổ sung 09/10/2026).

Mỗi ca là một file CSV nhỏ có chủ đích (đúng hoặc sai một kiểu) và kết quả
mong đợi: đọc được, hoặc DỪNG với thông báo chứa một cụm chữ cụ thể. Không cần
database: danh sách mã "có trong kho" là một tập mẫu.

Chạy từ thư mục backend:
    python test_bo_de.py
Mã thoát 0 = mọi ca đạt.
"""
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bo_doc_csv import LoiBoDe  # noqa: E402
import danh_gia_tu_nhien as TN  # noqa: E402
import danh_gia_tro_ly as TL  # noqa: E402

KHO = {"1.000001", "1.000002", "1.000003", "1.000010"}
Y_DINH = ["ho_so", "trinh_tu", "noi_nop", "le_phi", "thoi_han", "dieu_kien", "ket_qua", "can_cu", "doi_tuong"]
TAM = Path(tempfile.mkdtemp(prefix="test_bo_de_"))
DAT, TRUOT = [], []

H_TN = "stt,cau_hoi,loai,ma_thu_tuc_dung,ghi_chu\n"
H_TL = "stt,cau_hoi,y_dinh_dung,ma_thu_tuc_dung,ghi_chu\n"


def ghi(ten, noi_dung, ma_hoa="utf-8"):
    p = TAM / ten
    p.write_bytes(noi_dung.encode(ma_hoa) if isinstance(noi_dung, str) else noi_dung)
    return p


def ca(ten, ham, noi_dung, loi_chua=None, so_cau=None, ma_hoa="utf-8"):
    """loi_chua=None: phải đọc được (và đúng so_cau nếu có); ngược lại phải DỪNG với thông báo chứa chuỗi đó."""
    p = ghi(f"ca_{len(DAT) + len(TRUOT) + 1:02d}.csv", noi_dung, ma_hoa)
    try:
        de = ham(p)
        ok = loi_chua is None and (so_cau is None or len(de) == so_cau)
        chi_tiet = f"đọc được {len(de)} câu" + (f", mong đợi lỗi chứa '{loi_chua}'" if loi_chua else "")
    except LoiBoDe as e:
        thong_bao = "\n".join(e.loi)
        ok = loi_chua is not None and loi_chua.lower() in thong_bao.lower()
        chi_tiet = thong_bao.replace("\n", " | ")[:220]
    except Exception as e:  # mọi ngoại lệ khác là lỗi của bộ đọc
        ok, chi_tiet = False, f"ngoại lệ không mong đợi {type(e).__name__}: {e}"
    (DAT if ok else TRUOT).append(ten)
    print(("  ĐẠT   " if ok else "  TRƯỢT ") + ten + ("" if ok else f"   <- {chi_tiet}"))


tn = lambda p: TN.doc_bo_de(p, KHO)[0]           # noqa: E731
tl = lambda p: TL.doc_bo_de(p, KHO, Y_DINH)[0]   # noqa: E731

print("A. Bộ đo câu hỏi tự nhiên — file hợp lệ")
ca("A1 file chuẩn", tn, H_TN + "1,đăng ký khai sinh,tu_nhien,1.000001,\n2,cách nấu phở,ngoai_pham_vi,KHONG_CO,\n", so_cau=2)
ca("A2 dấu chấm phẩy (Excel vùng Việt Nam)", tn, H_TN.replace(",", ";") + "1;đăng ký khai sinh;tu_nhien;1.000001;\n", so_cau=1)
ca("A3 có BOM, xuống dòng Windows", tn, ("\ufeff" + H_TN + "1,a b c,tu_nhien,1.000001,\n").replace("\n", "\r\n"), so_cau=1)
ca("A4 ô ghi chú có xuống dòng trong nháy kép", tn, H_TN + '1,a b c,tu_nhien,1.000001,"dòng một\ndòng hai"\n2,d e f,tu_nhien,1.000002,\n', so_cau=2)
ca("A5 dấu phẩy trong câu hỏi được đặt trong nháy", tn, H_TN + '1,"hộ chiếu, visa",tu_nhien,1.000001,\n', so_cau=1)
ca("A6 nhiều mã, cách nhau dấu chấm phẩy", tn, H_TN + '1,a b c,tu_nhien,"1.000001; 1.000002",\n', so_cau=1)
ca("A7 câu trong phạm vi chưa gán nhãn (được phép)", tn, H_TN + "1,a b c,tu_nhien,,\n", so_cau=1)
ca("A8 dòng trống ở cuối file", tn, H_TN + "1,a b c,tu_nhien,1.000001,\n\n,,,,\n", so_cau=1)
ca("A9 cột trống ở cuối do Excel thêm, mọi ô trống", tn, H_TN.rstrip("\n") + ",,\n" + "1,a b c,tu_nhien,1.000001,,,\n", so_cau=1)

print("\nB. Bộ đo câu hỏi tự nhiên — lỗi cấu trúc bảng")
ca("B1 tiêu đề cột trùng", tn, "stt,cau_hoi,loai,ma_thu_tuc_dung,loai\n1,a,tu_nhien,1.000001,x\n", "trùng")
ca("B2 tiêu đề trùng chỉ khác khoảng trắng", tn, "stt,cau_hoi,loai,ma_thu_tuc_dung, ma_thu_tuc_dung \n1,a,tu_nhien,1.000001,\n", "trùng")
ca("B3 tiêu đề trùng chỉ khác hoa/thường", tn, "stt,cau_hoi,loai,ma_thu_tuc_dung,Loai\n1,a,tu_nhien,1.000001,x\n", "trùng")
ca("B4b cột trống ở cuối nhưng có dữ liệu", tn, H_TN.rstrip("\n") + ",\n" + "1,a,tu_nhien,1.000001,,x\n", "không có tên tiêu đề")
ca("B4 tiêu đề cột rỗng ở giữa", tn, "stt,cau_hoi,,loai,ma_thu_tuc_dung\n1,a,x,tu_nhien,1.000001\n", "không có tên")
ca("B5 thiếu cột bắt buộc", tn, "stt,cau_hoi,ma_thu_tuc_dung\n1,a,1.000001\n", "thiếu cột")
ca("B6 dòng thiếu ô", tn, H_TN + "1,a b c,tu_nhien\n", "thiếu ô")
ca("B7 dòng thừa ô có dữ liệu (phẩy trong câu không có nháy)", tn, H_TN + "1,hộ chiếu, visa,tu_nhien,1.000001,\n", "thừa ô")
ca("B8 nháy kép không đóng", tn, H_TN + '1,"a b c,tu_nhien,1.000001,\n2,d,tu_nhien,1.000002,\n', "nháy")
ca("B9 nháy kép đặt giữa ô", tn, H_TN + '1,"a" b,tu_nhien,1.000001,\n', "nháy")
ca("B10 số dòng báo lỗi là dòng THẬT khi có ô nhiều dòng", tn,
   H_TN + '1,a,tu_nhien,1.000001,"x\ny\nz"\n2,b,tu_nhien\n', "Dòng 5")
ca("B11 file không phải UTF-8", tn, H_TN + "1,café,tu_nhien,1.000001,\n", "UTF-8", ma_hoa="cp1252")
ca("B12 file rỗng", tn, "", "trống")
ca("B13 chỉ có dòng tiêu đề", tn, H_TN, "không có câu hỏi")

print("\nC. Bộ đo câu hỏi tự nhiên — lỗi nhãn")
ca("C1 câu ngoài phạm vi để trống nhãn", tn, H_TN + "1,cách nấu phở,ngoai_pham_vi,,\n", "KHONG_CO")
ca("C2 câu ngoài phạm vi lại có mã", tn, H_TN + "1,cách nấu phở,ngoai_pham_vi,1.000001,\n", "KHONG_CO")
ca("C3 KHONG_CO đi cùng mã", tn, H_TN + "1,a,tu_nhien,KHONG_CO;1.000001,\n", "mâu thuẫn")
ca("C4 loại câu lạ", tn, H_TN + "1,a,tu_nhien_x,1.000001,\n", "không hợp lệ")
ca("C5 STT trùng", tn, H_TN + "1,a,tu_nhien,1.000001,\n1,b,tu_nhien,1.000002,\n", "STT trùng")
ca("C6 câu trùng (khác hoa/thường)", tn, H_TN + "1,Đăng ký,tu_nhien,1.000001,\n2,đăng ký,tu_nhien,1.000002,\n", "trùng")
ca("C7 câu trùng (khác dạng Unicode NFC/NFD)", tn,
   H_TN + "1," + unicodedata.normalize("NFC", "đăng ký kết hôn") + ",tu_nhien,1.000001,\n2,"
   + unicodedata.normalize("NFD", "đăng ký kết hôn") + ",tu_nhien,1.000002,\n", "trùng")
ca("C8 mã bị Excel cắt số 0 cuối, có gợi ý", tn, H_TN + "1,a,tu_nhien,1.00001,\n", "có phải 1.000010")
ca("C9 mã không có trong kho", tn, H_TN + "1,a,tu_nhien,9.999999,\n", "không có trong kho")
ca("C10 mã sai dạng", tn, H_TN + "1,a,tu_nhien,abc,\n", "không đúng dạng")
ca("C11 thiếu câu hỏi", tn, H_TN + "1,,tu_nhien,1.000001,\n", "thiếu câu hỏi")
ca("C12 thiếu STT", tn, H_TN + ",a,tu_nhien,1.000001,\n", "thiếu STT")

print("\nD. Bộ đo trợ lý (dùng chung bộ đọc cấu trúc)")
ca("D1 file chuẩn", tl, H_TL + "1,a cần gì,ho_so,1.000001,\n2,phở,,KHONG_CO,\n", so_cau=2)
ca("D2 câu chưa gán nhãn bị chặn", tl, H_TL + "1,a cần gì,ho_so,,\n", "chưa gán nhãn")
ca("D3 ý định lạ", tl, H_TL + "1,a,hoso,1.000001,\n", "không hợp lệ")
ca("D4 câu ngoài phạm vi có ý định", tl, H_TL + "1,phở,ho_so,KHONG_CO,\n", "không được có ý định")
ca("D5 tiêu đề trùng", tl, "stt,cau_hoi,y_dinh_dung,ma_thu_tuc_dung,cau_hoi\n1,a,ho_so,1.000001,b\n", "trùng")
ca("D6 dòng thừa ô có dữ liệu", tl, H_TL + "1,a, b,ho_so,1.000001,\n", "thừa ô")
ca("D7 mã sai dạng", tl, H_TL + "1,a,ho_so,1.1,\n", "không đúng dạng")
ca("D8 mã không có trong kho", tl, H_TL + "1,a,ho_so,9.999999,\n", "không có trong kho")
ca("D9 STT trùng", tl, H_TL + "1,a,ho_so,1.000001,\n1,b,ho_so,1.000002,\n", "STT trùng")

print("\n" + "=" * 60)
print(f"KẾT QUẢ: {len(DAT)}/{len(DAT) + len(TRUOT)} ca đạt")
if TRUOT:
    print("Ca trượt:\n  " + "\n  ".join(TRUOT))
sys.exit(1 if TRUOT else 0)
