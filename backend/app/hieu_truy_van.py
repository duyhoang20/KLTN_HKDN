"""
Hiểu câu hỏi của người dân trước khi tra cứu (bổ sung ngày 08/10/2026).

VẤN ĐỀ
    Tên thủ tục trong kho viết bằng ngôn ngữ hành chính ("Cấp giấy chứng nhận
    quyền sử dụng đất lần đầu"), còn người dân hỏi bằng lời thường ("làm sổ đỏ
    cần những gì"). BM25 chỉ so khớp mặt chữ nên hụt ở hai chỗ:

      1. TỪ ĐỆM của câu hỏi ("cần những gì", "như thế nào", "ở đâu", "cho tôi
         hỏi") không mang nội dung nhưng vẫn bị tính vào mẫu số phần trăm,
         làm câu hỏi đúng chủ đề bị rớt dưới ngưỡng và trả về rỗng.
      2. TỪ ĐỒNG NGHĨA / TÊN GỌI DÂN GIAN ("sổ đỏ", "visa", "bằng lái",
         "chứng minh nhân dân") không xuất hiện trong tên thủ tục.

CÁCH LÀM
    Một lớp tiền xử lý dựa trên TRI THỨC TƯỜNG MINH (hai bảng khai báo bên
    dưới), sinh ra một vài "biến thể" của câu hỏi. search.py chấm từng biến
    thể bằng đúng công thức BM25 cũ rồi lấy mức khớp cao nhất cho mỗi thủ tục.

    - Bảng TỪ ĐỆM là danh sách đóng các cụm hỏi/cụm lịch sự của tiếng Việt.
      Đồng thời mỗi cụm cho biết Ý ĐỊNH của người hỏi (hỏi hồ sơ, lệ phí,
      thời hạn, nơi nộp, trình tự...) để trợ lý AI chọn đúng mục trả lời.
    - Bảng ĐỒNG NGHĨA ánh xạ cách gọi dân gian / viết tắt sang thuật ngữ
      hành chính. Mỗi dòng là một tri thức ngôn ngữ kiểm tra được bằng mắt,
      không phải số liệu học từ bộ đề.

ĐIỀU CỐ Ý KHÔNG LÀM (bài học ngày 28–29/09)
    KHÔNG coi một từ là từ đệm chỉ vì nó "không có trong kho". Từ nội dung
    không có trong kho ("phở", "iPhone", "xổ số") chính là dấu hiệu câu hỏi
    nằm ngoài phạm vi và phải được giữ trong mẫu số để hệ thống biết từ chối.
    Ở đây chỉ bỏ những cụm được liệt kê đích danh.

    Câu gốc của người dùng LUÔN là một biến thể, nên truy vấn nào không chứa
    từ đệm hay từ đồng nghĩa thì cho kết quả giống hệt trước khi có lớp này.
"""
import os
import re
import unicodedata
from typing import Dict, List, Tuple

SO_BIEN_THE_TOI_DA = 4


def _bo_dau(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _am_tiet(text: str) -> List[str]:
    """Chữ thường, NFC, giữ dấu, tách âm tiết (cùng quy tắc với search.norm_dau)."""
    text = unicodedata.normalize("NFC", (text or "").lower())
    text = re.sub(r"[^0-9a-zà-ỹđ\s]", " ", text)
    return text.split()


# ============================ BẢNG TỪ ĐỆM ============================
# (cụm, ý định hoặc None, vị trí)  — vị trí: "moi" = ở đâu cũng bỏ,
# "dau" = chỉ bỏ khi đứng đầu câu, "cuoi" = chỉ bỏ khi đứng cuối câu.
Y_DINH_TEN = {
    "ho_so": "Thành phần hồ sơ",
    "trinh_tu": "Trình tự thực hiện",
    "noi_nop": "Nơi nộp và cách thức nộp",
    "le_phi": "Phí, lệ phí",
    "thoi_han": "Thời hạn giải quyết",
    "dieu_kien": "Yêu cầu, điều kiện",
    "ket_qua": "Kết quả thực hiện",
    "can_cu": "Căn cứ pháp lý",
    "doi_tuong": "Đối tượng thực hiện",
}

TU_DEM: List[Tuple[str, str, str]] = [
    # --- hỏi hồ sơ, giấy tờ ---
    ("cần chuẩn bị những giấy tờ gì", "ho_so", "moi"),
    ("cần chuẩn bị giấy tờ gì", "ho_so", "moi"),
    ("cần những giấy tờ gì", "ho_so", "moi"),
    ("cần chuẩn bị những gì", "ho_so", "moi"),
    ("hồ sơ gồm những gì", "ho_so", "moi"),
    ("cần mang theo gì", "ho_so", "moi"),
    ("cần giấy tờ gì", "ho_so", "moi"),
    ("cần chuẩn bị gì", "ho_so", "moi"),
    ("gồm những gì", "ho_so", "moi"),
    ("cần những gì", "ho_so", "moi"),
    ("cần hồ sơ gì", "ho_so", "moi"),
    ("giấy tờ gì", "ho_so", "moi"),
    ("hồ sơ gì", "ho_so", "moi"),
    ("cần gì", "ho_so", "moi"),
    # --- hỏi trình tự, cách làm ---
    ("phải làm thế nào", "trinh_tu", "moi"),
    ("thì phải làm sao", "trinh_tu", "moi"),
    ("làm như thế nào", "trinh_tu", "moi"),
    ("gồm những bước nào", "trinh_tu", "moi"),
    ("làm thủ tục gì", "trinh_tu", "moi"),
    ("phải làm sao", "trinh_tu", "moi"),
    ("phải làm gì", "trinh_tu", "moi"),
    ("cần làm gì", "trinh_tu", "moi"),
    ("như thế nào", "trinh_tu", "moi"),
    ("làm thế nào", "trinh_tu", "moi"),
    ("các bước", "trinh_tu", "moi"),
    ("thế nào", "trinh_tu", "moi"),
    ("làm sao", "trinh_tu", "moi"),
    ("ra sao", "trinh_tu", "moi"),
    ("làm gì", "trinh_tu", "cuoi"),
    # --- hỏi nơi nộp ---
    ("nộp hồ sơ ở đâu", "noi_nop", "moi"),
    ("đến cơ quan nào", "noi_nop", "moi"),
    ("ở cơ quan nào", "noi_nop", "moi"),
    ("cơ quan nào", "noi_nop", "moi"),
    ("nộp ở đâu", "noi_nop", "moi"),
    ("làm ở đâu", "noi_nop", "moi"),
    ("đến đâu", "noi_nop", "moi"),
    ("tại đâu", "noi_nop", "moi"),
    ("ở đâu", "noi_nop", "moi"),
    # --- hỏi phí ---
    ("hết bao nhiêu tiền", "le_phi", "moi"),
    ("mất bao nhiêu tiền", "le_phi", "moi"),
    ("tốn bao nhiêu tiền", "le_phi", "moi"),
    ("lệ phí bao nhiêu", "le_phi", "moi"),
    ("phí bao nhiêu", "le_phi", "moi"),
    ("bao nhiêu tiền", "le_phi", "moi"),
    ("tốn bao nhiêu", "le_phi", "moi"),
    ("có mất phí không", "le_phi", "moi"),
    ("có mất tiền không", "le_phi", "moi"),
    # --- hỏi thời hạn ---
    ("mất bao nhiêu ngày", "thoi_han", "moi"),
    ("trong bao lâu", "thoi_han", "moi"),
    ("mất bao lâu", "thoi_han", "moi"),
    ("bao nhiêu ngày", "thoi_han", "moi"),
    ("mấy ngày", "thoi_han", "moi"),
    ("bao lâu", "thoi_han", "moi"),
    ("khi nào xong", "thoi_han", "moi"),
    ("khi nào có", "thoi_han", "moi"),
    # --- hỏi điều kiện ---
    ("cần điều kiện gì", "dieu_kien", "moi"),
    ("điều kiện gì", "dieu_kien", "moi"),
    ("có được không", "dieu_kien", "cuoi"),
    # --- lời dẫn, lịch sự: không mang ý định ---
    ("cho tôi hỏi", None, "moi"),
    ("cho mình hỏi", None, "moi"),
    ("cho em hỏi", None, "moi"),
    ("cho hỏi", None, "moi"),
    ("xin hỏi", None, "moi"),
    ("tôi muốn hỏi", None, "dau"),
    ("mình muốn hỏi", None, "dau"),
    ("tôi muốn", None, "dau"),
    ("mình muốn", None, "dau"),
    ("em muốn", None, "dau"),
    ("tôi cần", None, "dau"),
    ("mình cần", None, "dau"),
    ("em cần", None, "dau"),
    ("làm ơn", None, "moi"),
    ("giúp tôi", None, "moi"),
    ("giúp mình", None, "moi"),
    ("muốn", None, "dau"),
    ("cách", None, "dau"),
    ("xin", None, "dau"),
    ("làm", None, "dau"),
    ("tôi", None, "dau"),
    ("mình", None, "dau"),
    ("thì", None, "moi"),
    ("ạ", None, "cuoi"),
    ("nhỉ", None, "cuoi"),
    ("nhé", None, "cuoi"),
    ("vậy", None, "cuoi"),
    ("à", None, "cuoi"),
    ("gì", None, "cuoi"),
]

# Từ khóa cho biết ý định nhưng KHÔNG bị bỏ khỏi câu (vì cũng có thể là nội dung).
GOI_Y_Y_DINH: List[Tuple[str, str]] = [
    ("hồ sơ", "ho_so"), ("giấy tờ", "ho_so"),
    ("lệ phí", "le_phi"), ("phí", "le_phi"), ("chi phí", "le_phi"),
    ("thời hạn", "thoi_han"), ("thời gian giải quyết", "thoi_han"),
    ("trình tự", "trinh_tu"), ("quy trình", "trinh_tu"),
    ("điều kiện", "dieu_kien"), ("căn cứ pháp lý", "can_cu"),
    ("nộp online", "noi_nop"), ("nộp trực tuyến", "noi_nop"),
]

# ============================ BẢNG ĐỒNG NGHĨA ============================
# cách gọi dân gian / viết tắt  ->  các cách viết trong văn bản hành chính.
# Mỗi phương án thay thế sinh một biến thể truy vấn. Chuỗi rỗng "" nghĩa là
# bỏ cụm đó đi (dùng khi thuật ngữ thay thế đã có sẵn trong câu).
DONG_NGHIA: List[Tuple[str, List[str]]] = [
    # --- đất đai, nhà ở ---
    ("sổ đỏ", ["giấy chứng nhận quyền sử dụng đất"]),
    ("sổ hồng", ["giấy chứng nhận quyền sử dụng đất quyền sở hữu tài sản gắn liền với đất"]),
    ("bìa đỏ", ["giấy chứng nhận quyền sử dụng đất"]),
    ("xây nhà", ["giấy phép xây dựng nhà ở riêng lẻ"]),
    # --- cư trú ---
    ("chuyển hộ khẩu", ["đăng ký thường trú"]),
    ("nhập hộ khẩu", ["đăng ký thường trú"]),
    ("tách hộ khẩu", ["tách hộ"]),
    ("tách khẩu", ["tách hộ"]),
    ("hộ khẩu", ["thường trú"]),
    ("tạm trú tạm vắng", ["tạm trú", "tạm vắng"]),
    # --- giấy tờ tùy thân ---
    ("chứng minh nhân dân", ["thẻ căn cước"]),
    ("chứng minh thư", ["thẻ căn cước"]),
    ("căn cước công dân", ["thẻ căn cước"]),
    ("cmnd", ["thẻ căn cước"]),
    ("cccd", ["thẻ căn cước"]),
    ("passport", ["hộ chiếu"]),
    ("visa", ["thị thực"]),
    ("giấy độc thân", ["giấy xác nhận tình trạng hôn nhân"]),
    ("xác nhận độc thân", ["xác nhận tình trạng hôn nhân"]),
    ("làm giấy khai sinh", ["đăng ký khai sinh"]),
    ("lấy chồng", ["kết hôn"]),
    ("lấy vợ", ["kết hôn"]),
    ("cưới vợ", ["kết hôn"]),
    ("cưới chồng", ["kết hôn"]),
    ("đổi tên trong giấy khai sinh", ["thay đổi cải chính hộ tịch"]),
    ("sửa tên trong giấy khai sinh", ["thay đổi cải chính hộ tịch"]),
    ("đổi họ tên", ["thay đổi cải chính hộ tịch"]),
    # --- giao thông ---
    ("bằng lái xe", ["giấy phép lái xe"]),
    ("bằng lái", ["giấy phép lái xe"]),
    ("gplx", ["giấy phép lái xe"]),
    ("đăng kiểm", ["kiểm định an toàn kỹ thuật và bảo vệ môi trường", "đăng kiểm"]),
    ("sang tên xe", ["đăng ký sang tên di chuyển xe"]),
    ("xe máy", ["xe mô tô xe gắn máy", "xe máy"]),
    ("flycam", ["tàu bay không người lái"]),
    ("drone", ["tàu bay không người lái"]),
    # --- doanh nghiệp, thuế ---
    ("hộ kinh doanh cá thể", ["hộ kinh doanh"]),
    ("kinh doanh hộ cá thể", ["hộ kinh doanh"]),
    ("hộ cá thể", ["hộ kinh doanh"]),
    ("kinh doanh hộ gia đình", ["hộ kinh doanh"]),
    ("mở công ty", ["đăng ký thành lập doanh nghiệp"]),
    ("thành lập công ty", ["đăng ký thành lập công ty", "đăng ký thành lập doanh nghiệp"]),
    ("công ty tnhh", ["công ty trách nhiệm hữu hạn"]),
    ("tnhh", ["trách nhiệm hữu hạn"]),
    ("trách nhiệm hữu hạn", ["trách nhiệm hữu hạn", "tnhh"]),
    ("mtv", ["một thành viên"]),
    ("mã số thuế", ["đăng ký thuế", "mã số thuế"]),
    ("mst", ["mã số thuế"]),
    ("thuế tncn", ["thuế thu nhập cá nhân"]),
    ("thuế gtgt", ["thuế giá trị gia tăng"]),
    ("thuế vat", ["thuế giá trị gia tăng"]),
    # --- giáo dục ---
    ("bằng tốt nghiệp", ["văn bằng tốt nghiệp", "bằng tốt nghiệp"]),
    ("bằng đại học", ["văn bằng tốt nghiệp đại học"]),
    ("nhà trẻ", ["nhà trẻ", "trường mầm non"]),
    # --- y tế, an sinh ---
    ("phòng khám tư nhân", ["phòng khám", "cơ sở khám bệnh chữa bệnh"]),
    ("phòng khám tư", ["phòng khám", "cơ sở khám bệnh chữa bệnh"]),
    ("nhà thuốc", ["cơ sở bán lẻ thuốc", "nhà thuốc"]),
    ("hiệu thuốc", ["cơ sở bán lẻ thuốc"]),
    ("tiệm thuốc", ["cơ sở bán lẻ thuốc"]),
    ("quán ăn", ["cơ sở kinh doanh dịch vụ ăn uống"]),
    ("nhà hàng", ["cơ sở kinh doanh dịch vụ ăn uống", "nhà hàng"]),
    ("vệ sinh an toàn thực phẩm", ["an toàn thực phẩm"]),
    ("bhxh", ["bảo hiểm xã hội"]),
    ("bhyt", ["bảo hiểm y tế"]),
    ("bhtn", ["bảo hiểm thất nghiệp"]),
    ("sổ bảo hiểm", ["sổ bảo hiểm xã hội"]),
    ("nghỉ hưu", ["hưởng lương hưu"]),
    ("lãnh lương hưu", ["hưởng lương hưu"]),
    ("nhận lương hưu", ["hưởng lương hưu"]),
    ("thai sản", ["chế độ thai sản"]),
    # --- văn hóa, tư pháp ---
    ("bản quyền tác giả", ["quyền tác giả"]),
    ("bản quyền", ["quyền tác giả", "bản quyền"]),
    ("công chứng bản sao", ["chứng thực bản sao"]),
    ("sao y bản chính", ["chứng thực bản sao từ bản chính"]),
    ("sao y", ["chứng thực bản sao"]),
    ("lý lịch tư pháp", ["phiếu lý lịch tư pháp"]),
    ("ubnd", ["ủy ban nhân dân"]),
    # --- hành động: lời thường -> động từ hành chính ---
    ("bị mất", ["cấp lại"]),
    ("bị hỏng", ["cấp lại", "cấp đổi"]),
    ("bị rách", ["cấp lại", "cấp đổi"]),
    ("làm lại", ["cấp lại"]),
    ("xin lại", ["cấp lại"]),
    ("mới mua", ["lần đầu"]),
    ("lần đầu tiên", ["lần đầu"]),
]


# Từ chỉ nhắc lại ngữ cảnh ("còn lệ phí thì sao", "thủ tục này cần gì"): nếu sau
# khi bỏ từ đệm câu hỏi chỉ còn các từ này thì đó là câu HỎI TIẾP về thủ tục
# đang nói tới, không phải một chủ đề mới.
TU_NGU_CANH = ["thủ tục này", "thủ tục đó", "thủ tục trên", "cái này", "còn", "thì sao", "sao",
               "này", "đó", "nó", "vậy", "thế", "và", "với", "nữa", "thì", "của", "là",
               "hồ sơ", "giấy tờ", "lệ phí", "phí", "chi phí", "thời hạn", "thời gian",
               "trình tự", "quy trình", "điều kiện", "yêu cầu", "kết quả", "căn cứ pháp lý",
               "đối tượng", "nơi nộp", "nộp", "giải quyết", "thực hiện"]


def _khoa(cum: str, co_dau: bool) -> Tuple[str, ...]:
    toks = _am_tiet(cum)
    return tuple(toks if co_dau else [_bo_dau(t) for t in toks])


def _bang(co_dau: bool):
    """Dựng bảng tra theo dạng có dấu / không dấu, cụm dài xét trước."""
    dem = sorted(((_khoa(c, co_dau), y, vt) for c, y, vt in TU_DEM),
                 key=lambda x: -len(x[0]))
    dn = sorted(((_khoa(c, co_dau), thay) for c, thay in DONG_NGHIA),
                key=lambda x: -len(x[0]))
    goi_y = [(_khoa(c, co_dau), y) for c, y in GOI_Y_Y_DINH]
    nc = sorted((_khoa(c, co_dau) for c in TU_NGU_CANH), key=lambda x: -len(x))
    return dem, dn, goi_y, nc


_BANG = {True: _bang(True), False: _bang(False)}


def _tim(toks: List[str], khoa: Tuple[str, ...], tu: int = 0) -> int:
    n = len(khoa)
    for i in range(tu, len(toks) - n + 1):
        if tuple(toks[i:i + n]) == khoa:
            return i
    return -1


def phan_tich(query: str) -> Dict:
    """
    Trả về:
      goc        câu người dùng gõ
      bien_the   danh sách chuỗi truy vấn sẽ được chấm điểm (phần tử đầu luôn là câu gốc)
      y_dinh     danh sách mã ý định (xem Y_DINH_TEN)
      tu_dem     các cụm từ đệm đã bỏ
      dong_nghia [(cụm người dùng gõ, [thuật ngữ hành chính đã thay])]
      chu_de     câu hỏi sau khi bỏ từ đệm (phần "nội dung" của câu)
      hoi_tiep   True nếu câu chỉ nêu ý định mà không nêu chủ đề ("còn lệ phí thì sao")
    """
    goc = query or ""
    toks = _am_tiet(goc)
    kq = {"goc": goc, "bien_the": [goc], "y_dinh": [], "tu_dem": [],
          "dong_nghia": [], "chu_de": " ".join(toks), "hoi_tiep": False}
    if not toks:
        return kq
    kd = [_bo_dau(t) for t in toks]
    if any(not t for t in kd):
        return kq                      # ký tự lạ: giữ nguyên, không phân tích
    co_dau = kd != toks
    so = list(toks if co_dau else kd)  # dãy dùng để so khớp (bản sao)
    dem, dn, goi_y, ngu_canh = _BANG[co_dau]
    hien = list(toks)                  # dãy hiển thị/chấm điểm, song song với `so`

    # 1) Bỏ từ đệm, ghi nhận ý định
    y_dinh: List[str] = []
    doi, tron_cau = True, False
    while doi and not tron_cau:
        doi = False
        for khoa, y, vt in dem:
            if len(khoa) > len(so):
                continue
            if vt == "dau":
                i = 0 if tuple(so[:len(khoa)]) == khoa else -1
            elif vt == "cuoi":
                i = len(so) - len(khoa) if tuple(so[-len(khoa):]) == khoa else -1
            else:
                i = _tim(so, khoa)
            if i < 0:
                continue
            if len(so) == len(khoa):
                # Phần còn lại của câu chỉ gồm đúng cụm này: giữ nguyên chữ (không
                # để truy vấn thành rỗng), ghi nhận ý định rồi dừng bỏ từ đệm.
                if y and y not in y_dinh:
                    y_dinh.append(y)
                tron_cau = True
                break
            kq["tu_dem"].append(" ".join(hien[i:i + len(khoa)]))
            if y and y not in y_dinh:
                y_dinh.append(y)
            del so[i:i + len(khoa)]
            del hien[i:i + len(khoa)]
            doi = True
            break
    for khoa, y in goi_y:
        if _tim(so, khoa) >= 0 and y not in y_dinh:
            y_dinh.append(y)
    kq["y_dinh"] = y_dinh
    # Câu hỏi tiếp: có ý định nhưng không còn từ nào chỉ chủ đề
    con = list(so)
    for khoa in ngu_canh:
        while True:
            i = _tim(con, khoa)
            if i < 0:
                break
            del con[i:i + len(khoa)]
    kq["hoi_tiep"] = bool(y_dinh) and (tron_cau or not con)
    sach = " ".join(hien)
    kq["chu_de"] = sach

    # 2) Thay từ đồng nghĩa: mỗi phương án sinh một biến thể
    cho: List[Tuple[int, int, List[str]]] = []      # (vị trí, độ dài, phương án)
    da_dung = [False] * len(so)
    for khoa, thay in dn:
        tu = 0
        while True:
            i = _tim(so, khoa, tu)
            if i < 0:
                break
            if not any(da_dung[i:i + len(khoa)]):
                for j in range(i, i + len(khoa)):
                    da_dung[j] = True
                cho.append((i, len(khoa), thay))
                kq["dong_nghia"].append((" ".join(hien[i:i + len(khoa)]), [t for t in thay if t]))
            tu = i + 1
    cho.sort()

    bien_the = [goc]
    if sach and len(hien) != len(toks):
        bien_the.append(sach)
    if cho:
        so_pa = max(len(c[2]) for c in cho)
        for k in range(so_pa):
            out, p = [], 0
            for i, n, thay in cho:
                out.extend(hien[p:i])
                pa = thay[min(k, len(thay) - 1)]
                pa_toks = _am_tiet(pa) if co_dau else [_bo_dau(t) for t in _am_tiet(pa)]
                out.extend(pa_toks)
                p = i + n
            out.extend(hien[p:])
            # bỏ cụm lặp liền kề do thay thế tạo ra ("cấp lại ... cấp lại")
            out = _bo_lap(out)
            bien_the.append(" ".join(out))
    # loại trùng, giữ thứ tự, giới hạn số biến thể
    xem, gon = set(), []
    for b in bien_the:
        k = " ".join(_am_tiet(b))
        if k and k not in xem:
            xem.add(k)
            gon.append(b)
    kq["bien_the"] = gon[:SO_BIEN_THE_TOI_DA] or [goc]
    if not lop_hieu_cau_hoi_bat():
        # Công tắc trong .env: HIEU_CAU_HOI=0 -> tra cứu chỉ dùng câu gốc, cho
        # kết quả giống hệt bản 29/09. Ý định vẫn được nhận để trợ lý chọn mục.
        kq["bien_the"], kq["tu_dem"], kq["dong_nghia"] = [goc], [], []
    return kq


def lop_hieu_cau_hoi_bat() -> bool:
    """Đọc công tắc HIEU_CAU_HOI trong .env (mặc định bật)."""
    return os.getenv("HIEU_CAU_HOI", "1").strip() not in ("0", "false", "False", "tat")


def _bo_lap(toks: List[str]) -> List[str]:
    """Bỏ lần xuất hiện thứ hai của một cặp âm tiết đã có (do thay đồng nghĩa)."""
    da, out, i = set(), [], 0
    while i < len(toks):
        if i + 1 < len(toks):
            cap = (toks[i], toks[i + 1])
            if cap in da and cap in {("cấp", "lại"), ("cap", "lai"), ("lần", "đầu"), ("lan", "dau")}:
                i += 2
                continue
            da.add(cap)
        out.append(toks[i])
        i += 1
    return out
