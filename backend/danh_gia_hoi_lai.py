"""Đo tác dụng của quy tắc “hỏi lại khi các thủ tục gần giống nhau” (bổ sung 21/10/2026).

Chạy trợ lý THẬT (tro_ly.tra_loi, không dùng mô hình ngôn ngữ) trên các bộ câu hỏi tự nhiên, hai lần:
TẮT quy tắc (như bản 20/10) và BẬT quy tắc. Với mỗi câu có nhãn (mã thủ tục đúng) đếm:
  - trả lời đúng thủ tục; trả lời SAI thủ tục (khẳng định nhầm, lỗi nặng nhất);
  - hỏi lại, và trong đó các lựa chọn có chứa thủ tục đúng (người dùng bấm một lần là có câu trả lời đúng);
  - câu ngoài phạm vi mà vẫn bị trả lời.

    python danh_gia_hoi_lai.py
    python danh_gia_hoi_lai.py --luu ..\\bao_cao\\danh_gia_hoi_lai_Windows.txt

Tham số của quy tắc (tro_ly.NGUONG_GAN_NHAU, tro_ly.SO_TU_KHAC_BIET) được chọn trên bộ PHÁT TRIỂN.
Bộ kiểm tra độc lập, bộ ngoài phạm vi và bộ trợ lý chỉ dùng để báo cáo, không dùng để chọn tham số.
Nhãn các bộ đề là AI đề xuất, CHƯA được người duyệt (xem PHIEN_BAN.txt).
"""
import argparse
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
sys.path.insert(0, str(THU_MUC))
BO_DE = THU_MUC.parent / "bo_de_tu_nhien"
CAC_BO = [("Phát triển (dùng để chọn tham số)", "bo_de_phat_trien_NHAN_DE_XUAT.csv"),
          ("Kiểm tra độc lập", "bo_de_kiem_tra_doc_lap.csv"),
          ("Trợ lý (60 câu)", "bo_de_tro_ly.csv"),
          ("Ngoài phạm vi (60 câu)", "bo_de_ngoai_pham_vi_60.csv")]


def doc_bo(path: Path):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        ma = {t for t in re.split(r"[;\s]+", r.get("ma_thu_tuc_dung") or "") if t and t != "KHONG_CO"}
        out.append((r["cau_hoi"].strip(), ma))
    return out


def do(cac_cau, docs, tro_ly):
    c = Counter()
    for cau, ma in cac_cau:
        kq = tro_ly.tra_loi(cau, docs, dung_mo_hinh=False)
        tt = kq["trang_thai"]
        ngoai = not ma
        c["tong"] += 1
        c["ngoai" if ngoai else "trong"] += 1
        if tt == "tra_loi":
            if ngoai:
                c["ngoai_bi_tra_loi"] += 1
            elif kq["thu_tuc"]["ma_thu_tuc"] in ma:
                c["dung"] += 1
            else:
                c["sai"] += 1
        elif tt == "can_lam_ro":
            c["hoi_lai_ngoai" if ngoai else "hoi_lai"] += 1
            if not ngoai and any(x["ma_thu_tuc"] in ma for x in kq["lua_chon"]):
                c["hoi_lai_co_dap_an"] += 1
        else:
            c["tu_choi_ngoai" if ngoai else "tu_choi_nham"] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--luu", type=Path)
    a = ap.parse_args()
    from app.database import SessionLocal
    from app import models, tro_ly
    db = SessionLocal()
    docs = db.query(models.GuidanceDocument).filter(models.GuidanceDocument.status == "published").all()
    dong = ["=" * 78, "HỎI LẠI KHI CÁC THỦ TỤC GẦN GIỐNG NHAU — TÁC DỤNG TRÊN CÁC BỘ CÂU HỎI", "=" * 78,
            f"Kho: {len(docs)} thủ tục công khai. Tham số: NGUONG_GAN_NHAU={tro_ly.NGUONG_GAN_NHAU}, "
            f"SO_TU_KHAC_BIET={tro_ly.SO_TU_KHAC_BIET}, ngưỡng trả lời {tro_ly.NGUONG_TRA_LOI}%.",
            "Nhãn: AI đề xuất, CHƯA được người duyệt.", ""]
    goc = (tro_ly.NGUONG_GAN_NHAU, tro_ly.SO_TU_KHAC_BIET, list(tro_ly.TU_HANH_DONG))
    for ten, tep in CAC_BO:
        p = BO_DE / tep
        if not p.exists():
            continue
        cau = doc_bo(p)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        tro_ly.NGUONG_GAN_NHAU, tro_ly.SO_TU_KHAC_BIET, tro_ly.TU_HANH_DONG = 9.0, 999, []   # tắt quy tắc
        tat = do(cau, docs, tro_ly)
        tro_ly.NGUONG_GAN_NHAU, tro_ly.SO_TU_KHAC_BIET, tro_ly.TU_HANH_DONG = goc[0], goc[1], list(goc[2])
        bat = do(cau, docs, tro_ly)
        dong.append(f"{ten} — {tep} (SHA {sha}): {tat['trong']} câu trong phạm vi, {tat['ngoai']} câu ngoài phạm vi")
        dong.append(f"  {'':44}{'TẮT quy tắc':>14}{'BẬT quy tắc':>14}")
        for k, nhan in (("dung", "Trả lời đúng thủ tục"), ("sai", "Trả lời SAI thủ tục (khẳng định nhầm)"),
                        ("hoi_lai", "Hỏi lại (câu trong phạm vi)"),
                        ("hoi_lai_co_dap_an", "  trong đó lựa chọn có thủ tục đúng"),
                        ("tu_choi_nham", "Từ chối nhầm câu trong phạm vi"),
                        ("ngoai_bi_tra_loi", "Câu ngoài phạm vi vẫn bị trả lời")):
            dong.append(f"  {nhan:44}{tat[k]:>14}{bat[k]:>14}")
        tl = lambda c: f"{100 * c['dung'] / (c['dung'] + c['sai']):.1f}%" if c["dung"] + c["sai"] else "—"
        mot = lambda c: c["dung"] + c["hoi_lai_co_dap_an"]
        dong.append(f"  {'Tỉ lệ đúng trong các câu trả lời thẳng':44}{tl(tat):>14}{tl(bat):>14}")
        dong.append(f"  {'Có đáp án đúng sau tối đa một lần chọn':44}{mot(tat):>14}{mot(bat):>14}")
        dong.append("")
    dong += ["Cách đọc: quy tắc đổi một phần câu trả lời thẳng thành câu hỏi lại. Lợi: ít khẳng định nhầm hơn.",
             "Giá: người dùng phải bấm chọn thêm một lần ở các câu đó; một số câu vốn trả lời đúng cũng bị hỏi lại."]
    out = "\n".join(dong)
    print(out)
    if a.luu:
        a.luu.write_text(out + "\n", encoding="utf-8")
        print(f"\nĐã ghi: {a.luu}")


if __name__ == "__main__":
    main()
