"""Kiểm tra CHÍNH BỘ ĐỐI CHIẾU NGUỒN bằng lỗi cố ý (bổ sung 14/10/2026).

Câu hỏi cần trả lời trước hội đồng: “Bộ đối chiếu báo 576/576 thì có nghĩa gì,
nó có bắt được lỗi thật không?”. Cách làm (kiểm thử đột biến):

  1. Lấy câu trả lời ĐÚNG của trợ lý cho từng mục của 21 thủ tục mẫu.
  2. Cố ý làm sai MỘT chỗ theo từng kiểu lỗi (đổi đơn vị thời gian, đổi đơn vị
     tiền, đổi số tiền, đổi số bản, bỏ một dòng, cắt nửa nội dung, thêm câu
     “miễn lệ phí”...).
  3. Đưa bản sai vào doi_chieu_nguon.doi_chieu() và đếm số lần bộ đối chiếu
     PHÁT HIỆN (báo thiếu dữ kiện, dòng không căn cứ, hoặc dòng sai lệch).

Từ 15/10 có thêm ba kiểu lỗi “đúng số nhưng sai chủ thể”: lấy số bản, thời hạn
hoặc số tiền CÓ THẬT ở dòng khác của cùng mục gắn sang dòng này, kể cả thêm hẳn
một dòng mới (ví dụ do rà soát độc lập nêu). Tỉ lệ 100% chỉ có nghĩa với các kiểu
lỗi được liệt kê, không bao phủ mọi cách ghép sai.

Kiểu lỗi nào bộ đối chiếu không bắt được thì in ra đúng như vậy: đó là giới hạn
cần ghi vào báo cáo, không phải chỗ để sửa số cho đẹp.

Chạy:
    python kiem_tra_bo_doi_chieu.py
    python kiem_tra_bo_doi_chieu.py --luu ..\\bao_cao\\kiem_tra_bo_doi_chieu.txt
Không cần database; chỉ đọc ../bao_cao/mau_21_thu_tuc_du_lieu_chi_tiet.json.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import tro_ly  # noqa: E402  (chỉ để lấy câu trả lời đúng làm gốc)
import doi_chieu_nguon as DC  # noqa: E402

MAU = Path(__file__).resolve().parent.parent / "bao_cao" / "mau_21_thu_tuc_du_lieu_chi_tiet.json"


def _phat_hien(goc, data, y, dong) -> bool:
    r = DC.doi_chieu(data, y, dong)
    return bool(r["thieu"] or r["dong_khong_can_cu"] or r["dong_sai_lech"]) and r != goc


def _thay_dau(s, cu, moi):
    i = s.find(cu)
    return None if i < 0 else s[:i] + moi + s[i + len(cu):]


def _doi_so_tien(s):
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(\s*(?:đồng|USD))", s)
    if not m:
        return None
    so = m.group(1)
    moi = ("9" + so[1:]) if so[0] != "9" else ("1" + so[1:])
    return s[:m.start(1)] + moi + s[m.end(1):]


def _doi_so_ban(s):
    m = re.search(r"(\d+)( bản (?:chính|sao))", s)
    return None if not m else s[:m.start(1)] + str(int(m.group(1)) + 2) + s[m.end(1):]


DOT_BIEN = {
    "đổi đơn vị thời gian (ngày làm việc → tháng)": lambda s: _thay_dau(s, "ngày làm việc", "tháng"),
    "đổi đơn vị tiền (đồng → USD)": lambda s: _thay_dau(s, " đồng", " USD"),
    "đổi số tiền": _doi_so_tien,
    "đổi số bản chính/bản sao": _doi_so_ban,
    "cắt mất nửa sau của dòng": lambda s: s[: max(8, len(s) // 2)] if len(s) > 40 else None,
    "thêm câu “Miễn lệ phí.” (không có chữ số)": lambda s: s + " Miễn lệ phí." if s.startswith("- ") else None,
}


# Lỗi “đúng số nhưng sai chủ thể” (bổ sung 15/10 theo rà soát độc lập): lấy một cặp
# số–đơn vị CÓ THẬT ở dòng khác của cùng mục rồi gắn vào dòng này.
_RE_CHEO = {"ho_so": re.compile(r"(\d+ bản (?:chính|sao)(?:, \d+ bản sao)?)()"),
            "thoi_han": re.compile(r"(\d+)( ngày làm việc| ngày| tháng| giờ)"),
            "le_phi": re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)( đồng)")}


def _gia_tri(x):
    """“08” và “8” là cùng một số; cụm số bản so nguyên văn."""
    return int(x.replace(".", "")) if re.fullmatch(r"[\d.]+", x) else x


def _cheo(dong, i, y):
    """Thay số ở dòng i bằng số khác đơn vị-giống-hệt lấy từ một dòng khác; None nếu không có."""
    rx = _RE_CHEO.get(y)
    m = rx.search(dong[i]) if rx else None
    if not m:
        return None
    for j, d in enumerate(dong):
        if j == i:
            continue
        for n in rx.finditer(d):
            if n.group(2) == m.group(2) and _gia_tri(n.group(1)) != _gia_tri(m.group(1)):
                return dong[i][:m.start(1)] + n.group(1) + dong[i][m.end(1):]
    return None


CHEO = {"ho_so": "gắn số bản của giấy tờ khác (sửa dòng)",
        "thoi_han": "gắn thời hạn của hình thức nộp khác",
        "le_phi": "gắn số tiền của khoản phí khác"}
THEM_DONG = "thêm dòng: giấy tờ với số bản của giấy tờ khác"
GHEP_VE = "thêm dòng hai vế: số bản của B gắn vào A, B ở vế sau"
GHEP_VE_PHAY = "như trên, hai vế nối bằng dấu phẩy"
GHEP_VE_VA = "như trên, hai vế nối bằng chữ “và”"


def _ghep_ve(dong, i, noi=";"):
    """Bổ sung 20/10 bản 3 (báo cáo kiểm thử độc lập F06): giữ nguyên các dòng đúng, thêm dòng
    “A cần <số bản của B>; B có liên quan.” Bộ đối chiếu cũ gộp số của mọi chủ thể trong dòng nên
    bỏ lọt kiểu này."""
    rx = _RE_CHEO["ho_so"]
    m = rx.search(dong[i])
    if not m or " (" not in dong[i]:
        return None
    def ten(d, mm):                       # tên giấy tờ = phần trước “ (” mở cụm số bản (tên có thể chứa ngoặc)
        k = d.rfind(" (", 0, mm.start())
        return None if k < 0 else d[2 if d.startswith("- ") else 0:k]
    ten_a = ten(dong[i], m)
    if not ten_a:
        return None
    for j, d in enumerate(dong):
        n = rx.search(d)
        if j == i or not n or " (" not in d or DC._cap(DC._n(n.group(1))) <= DC._cap(DC._n(m.group(1))):
            continue                      # số bản của B cũng là của A thì không phải lỗi
        ten_b = ten(d, n)
        if not ten_b or ten_a in ten_b or ten_b in ten_a:
            continue
        return f"- {ten_a} cần {n.group(1)}{noi} {ten_b} có liên quan."
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--luu", type=Path)
    a = ap.parse_args()
    rows = json.loads(MAU.read_text(encoding="utf-8"))
    tong, bat = Counter(), Counter()
    vi_du_lot = {}
    for r in rows:
        data = r["data"]
        for y in tro_ly.DUNG_MUC:
            dong = tro_ly.trich_muc(data, [y])[0]["dong"]
            goc = DC.doi_chieu(data, y, dong)
            if goc["thieu"] or goc["dong_khong_can_cu"] or goc["dong_sai_lech"]:
                continue        # câu trả lời gốc đã có vấn đề thì không dùng làm gốc
            for i, s in enumerate(dong):
                if s.lower().startswith("trường hợp"):
                    continue
                # bỏ một dòng
                ten = "bỏ hẳn một dòng"
                tong[ten] += 1
                if _phat_hien(goc, data, y, dong[:i] + dong[i + 1:]):
                    bat[ten] += 1
                else:
                    vi_du_lot.setdefault(ten, f"{r['procedure_code']} [{y}] {s[:90]}")
                moi = _cheo(dong, i, y)
                if moi:
                    for ten, ban in ((CHEO[y], dong[:i] + [moi] + dong[i + 1:]),
                                     (THEM_DONG, dong + [moi]) if y == "ho_so" else (None, None)):
                        if not ten:
                            continue
                        tong[ten] += 1
                        if _phat_hien(goc, data, y, ban):
                            bat[ten] += 1
                        else:
                            vi_du_lot.setdefault(ten, f"{r['procedure_code']} [{y}] {moi[:90]}")
                for ten_ve, noi in ((GHEP_VE, ";"), (GHEP_VE_PHAY, ","), (GHEP_VE_VA, " và")):
                    moi = _ghep_ve(dong, i, noi) if y == "ho_so" else None
                    if moi:
                        tong[ten_ve] += 1
                        if _phat_hien(goc, data, y, dong + [moi]):
                            bat[ten_ve] += 1
                        else:
                            vi_du_lot.setdefault(ten_ve, f"{r['procedure_code']} [{y}] {moi[:90]}")
                for ten, f in DOT_BIEN.items():
                    moi = f(s)
                    if not moi or moi == s:
                        continue
                    tong[ten] += 1
                    if _phat_hien(goc, data, y, dong[:i] + [moi] + dong[i + 1:]):
                        bat[ten] += 1
                    else:
                        vi_du_lot.setdefault(ten, f"{r['procedure_code']} [{y}] {moi[:90]}")
    out = ["=" * 76, "KIỂM TRA BỘ ĐỐI CHIẾU NGUỒN BẰNG LỖI CỐ Ý", "=" * 76,
           f"Bộ đối chiếu : {DC.PHIEN_BAN}",
           f"Dữ liệu      : {MAU.name} ({len(rows)} thủ tục, câu trả lời gốc của trợ lý)",
           "Mỗi lần chỉ làm sai MỘT dòng của MỘT mục. “Phát hiện” = bộ đối chiếu báo thiếu",
           "dữ kiện, dòng không căn cứ, hoặc dòng sai lệch (cặp số–đơn vị không có trong nguồn hoặc của chủ thể khác).", "",
           f"{'Kiểu lỗi cố ý':<50}{'Phát hiện':>12}{'Tỉ lệ':>10}"]
    for ten in ["bỏ hẳn một dòng"] + list(DOT_BIEN) + list(CHEO.values()) + [THEM_DONG, GHEP_VE, GHEP_VE_PHAY, GHEP_VE_VA]:
        n, k = tong[ten], bat[ten]
        out.append(f"{ten:<50}{f'{k}/{n}':>12}{(f'{100 * k / n:.1f}%' if n else '—'):>10}")
    out += ["", "Ví dụ lỗi KHÔNG bị phát hiện (mỗi kiểu một ví dụ):"]
    for ten, vd in vi_du_lot.items():
        out.append(f"  [{ten}] {vd}")
    if not vi_du_lot:
        out.append("  (không có)")
    out += ["", "Cách đọc: kiểu lỗi có tỉ lệ thấp là việc bộ đối chiếu chưa làm được.",
            "Ví dụ câu “Miễn lệ phí.” không có chữ số nên chỉ được bắt khi nó làm mất dữ kiện;",
            "đây là lý do trợ lý không cho mô hình ngôn ngữ viết dữ kiện."]
    print("\n".join(out))
    if a.luu:
        a.luu.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\nĐã ghi: {a.luu}")


if __name__ == "__main__":
    main()
