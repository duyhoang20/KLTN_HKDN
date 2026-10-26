"""
Giao tiếp cơ bản của trợ lý (bổ sung 16/10/2026): chào hỏi, cám ơn, tạm biệt,
hỏi trợ lý là ai, làm được gì.

Nguyên tắc:
  - Chỉ nhận là “câu giao tiếp” khi TOÀN BỘ câu chỉ gồm các cụm khai báo đích
    danh dưới đây và các từ xưng hô, đệm (“bạn”, “ạ”, “nhé”...). Một câu có bất
    kỳ từ nội dung nào khác (“chào, làm hộ chiếu cần gì”) vẫn đi vào luồng tra
    cứu như cũ. Vì vậy lớp này không thể nuốt mất một câu hỏi về thủ tục.
  - Lời chào đứng ĐẦU một câu hỏi thật (“xin chào, cho hỏi làm hộ chiếu…”) được
    bóc ra trước khi tra cứu, để các âm tiết “xin”, “chào” không làm phình mẫu số
    độ khớp; câu trả lời được đánh dấu `chao` để giao diện đáp lại lời chào.
  - Câu đáp là khuôn mẫu cố định, không dùng mô hình ngôn ngữ, không chứa dữ kiện.
"""
import re
import unicodedata
from typing import Dict, List, Optional, Tuple


def _bo_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _tach(s: str) -> List[str]:
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.findall(r"[^\W_]+", s)


# Mỗi loại: các cụm (viết có dấu; bản không dấu tự sinh ra).
CUM = {
    "chao": [
        "xin chào", "chào", "chào bạn", "chào buổi sáng", "chào buổi chiều", "chào buổi tối",
        "hello", "hi", "hey", "helo", "alo", "a lô", "good morning", "good afternoon", "good evening",
    ],
    "cam_on": [
        "cảm ơn", "cám ơn", "xin cảm ơn", "xin cám ơn", "cảm ơn nhiều", "cám ơn nhiều",
        "thanks", "thank you", "thank", "tks", "thx",
    ],
    "tam_biet": [
        "tạm biệt", "hẹn gặp lại", "bye", "bye bye", "goodbye", "good bye", "bai",
    ],
    "gioi_thieu": [
        "bạn là ai", "bạn là gì", "bạn tên gì", "bạn tên là gì", "đây là đâu", "đây là trang gì",
        "bạn làm được gì", "bạn giúp được gì", "bạn có thể làm gì", "bạn có thể giúp gì",
        "bạn giúp gì được", "trợ lý làm được gì", "hướng dẫn sử dụng", "cách dùng",
        "who are you", "what can you do", "help",
    ],
    "hoi_tham": [
        "bạn khỏe không", "bạn có khỏe không", "khỏe không", "bạn ổn không", "how are you",
    ],
}

# Từ xưng hô, từ đệm có thể đi kèm một câu giao tiếp mà không làm đổi ý.
TU_DEM = {
    "bạn", "ạ", "à", "nhé", "nha", "nhá", "ơi", "trợ", "lý", "em", "anh", "chị", "ad", "admin",
    "bot", "ok", "oke", "okay", "vâng", "dạ", "rất", "nhiều", "lắm", "luôn", "nhiều", "nhé", "hệ",
    "thống", "mình", "tôi", "all", "there", "very", "much", "so", "you", "a", "vậy", "thì",
}

_BANG: List[Tuple[Tuple[str, ...], str]] = []
for _loai, _ds in CUM.items():
    for _c in _ds:
        for _bien in {_c, _bo_dau(_c)}:
            _BANG.append((tuple(_tach(_bien)), _loai))
_BANG.sort(key=lambda x: -len(x[0]))                         # cụm dài khớp trước
_TU_DEM = TU_DEM | {_bo_dau(w) for w in TU_DEM}


def _khop_tai(tu: List[str], i: int) -> Optional[Tuple[int, str]]:
    for cum, loai in _BANG:
        if tuple(tu[i:i + len(cum)]) == cum:
            return len(cum), loai
    return None


def nhan_dien(cau: str) -> Optional[str]:
    """Trả về loại giao tiếp nếu CẢ CÂU chỉ là giao tiếp; ngược lại None."""
    tu = _tach(cau)
    if not tu:
        return None
    i, cac_loai = 0, []
    while i < len(tu):
        k = _khop_tai(tu, i)
        if k:
            cac_loai.append(k[1])
            i += k[0]
        elif tu[i] in _TU_DEM:
            i += 1
        else:
            return None
    if not cac_loai:
        return None
    # “chào, cảm ơn” → ưu tiên ý cuối cùng có nội dung (cảm ơn / tạm biệt / giới thiệu)
    for uu_tien in ("gioi_thieu", "tam_biet", "cam_on", "hoi_tham", "chao"):
        if uu_tien in cac_loai:
            return uu_tien
    return cac_loai[0]


def boc_loi_chao(cau: str) -> Tuple[str, bool]:
    """Bóc lời chào, lời cám ơn ở ĐẦU một câu hỏi thật.

    “Xin chào, cho hỏi làm hộ chiếu” → (“cho hỏi làm hộ chiếu”, True). Chỉ bóc khi
    phần đầu gồm toàn cụm giao tiếp và từ xưng hô, có dấu câu ngăn cách với phần sau
    (hoặc là cụm chào hai từ như “xin chào”, “chào bạn”), và phần sau vẫn có nội dung.
    Nhờ vậy “chào cờ”, “hi vọng”, “chào bán cổ phần” không bị cắt nhầm.
    """
    s = unicodedata.normalize("NFC", cau or "")
    toks = [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"[^\W_]+", s)]
    tu = [t[0] for t in toks]
    i, co_cum, nhieu_tu = 0, False, False
    while i < len(tu):
        k = _khop_tai(tu, i)
        if k:
            co_cum = True
            nhieu_tu = nhieu_tu or (k[1] == "chao" and k[0] >= 2)
            i += k[0]
        elif tu[i] in _TU_DEM:
            nhieu_tu = nhieu_tu or tu[i] in ("bạn", "ban", "anh", "chị", "chi", "em", "ad", "admin")
            i += 1
        else:
            break
    if not co_cum or i >= len(tu):
        return cau, False
    giua = s[toks[i - 1][2]:toks[i][1]]
    if not re.search(r"[,.!?;:\-–]", giua) and not nhieu_tu:
        return cau, False
    return s[toks[i][1]:].strip(), True


GOI_Y = [
    "Đăng ký khai sinh cần giấy tờ gì?",
    "Cấp lại căn cước bị mất lệ phí bao nhiêu?",
    "Đăng ký tạm trú nộp ở đâu?",
]

CAU_DAP = {
    "chao": ("Chào bạn! Tôi là trợ lý tra cứu thủ tục hành chính. Bạn cần tìm hiểu thủ tục nào? "
             "Bạn có thể hỏi về hồ sơ, lệ phí, thời hạn hoặc nơi nộp của một thủ tục."),
    "cam_on": "Không có gì ạ. Nếu cần tra cứu thêm thủ tục nào, bạn cứ hỏi tiếp nhé.",
    "tam_biet": "Tạm biệt bạn! Chúc bạn hoàn tất thủ tục thuận lợi. Khi cần, bạn quay lại hỏi tiếp nhé.",
    "gioi_thieu": ("Tôi là trợ lý tra cứu thủ tục hành chính của hệ thống này. Bạn hỏi về một thủ tục, "
                   "tôi tìm thủ tục phù hợp rồi trích đúng mục bạn cần: thành phần hồ sơ, lệ phí, thời hạn, "
                   "nơi nộp, trình tự hoặc điều kiện, kèm nguồn để bạn đối chiếu. Tôi không tiếp nhận hồ sơ "
                   "và chỉ trả lời về thủ tục hành chính."),
    "hoi_tham": "Cảm ơn bạn đã hỏi thăm, tôi luôn sẵn sàng. Bạn cần tra cứu thủ tục nào?",
}


def tra_loi_giao_tiep(loai: str) -> Dict:
    return {"loai": loai, "tra_loi": CAU_DAP[loai], "goi_y": [] if loai == "tam_biet" else list(GOI_Y)}
