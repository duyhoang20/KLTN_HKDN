"""Tính kết quả khảo sát người dùng (bổ sung 21/10/2026).

    python tinh_ket_qua.py ket_qua_khao_sat.csv

Tệp CSV theo mẫu ket_qua_khao_sat_MAU.csv: mỗi dòng là một nhiệm vụ của một người thử. Điểm SUS
(10 câu, thang 1–5) chỉ cần điền ở MỘT dòng của mỗi người. Công thức SUS chuẩn (Brooke, 1996):
câu lẻ (1,3,5,7,9) lấy điểm − 1, câu chẵn lấy 5 − điểm, cộng lại rồi nhân 2,5 (thang 0–100).
Mốc tham khảo thường dùng: khoảng 68 là mức trung bình.
"""
import csv
import statistics
import sys
from collections import defaultdict


def sus(d):
    v = [int((d[f"sus{i}"] or "").strip()) for i in range(1, 11)]
    if any(x < 1 or x > 5 for x in v):
        raise ValueError("điểm SUS phải từ 1 đến 5")
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(v))


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    # Kiểm tra dữ liệu nhập (bổ sung 21/10 bản 2): báo lỗi thay vì âm thầm lấy một dòng.
    canh_bao, giu, cap, dong_sus = [], [], set(), defaultdict(list)
    for so, r in enumerate(rows, 2):
        ma = (r.get("ma_nguoi_thu") or "").strip()
        if not ma:
            canh_bao.append(f"dòng {so}: thiếu mã người thử, bỏ dòng này")
            continue
        if ma.upper().startswith("VI_DU"):
            canh_bao.append(f"dòng {so}: dòng ví dụ {ma}, bỏ dòng này (xóa khỏi tệp trước khi báo cáo)")
            continue
        tg = (r.get("thoi_gian_giay") or "").strip()
        if tg:
            try:
                if float(tg) < 0:
                    raise ValueError
            except ValueError:
                canh_bao.append(f"dòng {so}: thời gian “{tg}” không hợp lệ, để trống ô này")
                r["thoi_gian_giay"] = ""
        if (ma, r.get("nhiem_vu")) in cap:
            canh_bao.append(f"dòng {so}: {ma} làm {r.get('nhiem_vu')} hai lần, chỉ tính lần đầu")
            continue
        cap.add((ma, r.get("nhiem_vu")))
        if any((r.get(f"sus{i}") or "").strip() for i in range(1, 11)):
            dong_sus[ma].append(so)
        giu.append(r)
    rows = giu
    nguoi = sorted({r["ma_nguoi_thu"] for r in rows})
    diem_sus = {}
    theo_nv = defaultdict(list)
    for r in rows:
        ma = r["ma_nguoi_thu"]
        if any((r.get(f"sus{i}") or "").strip() for i in range(1, 11)) and len(dong_sus[ma]) == 1:
            try:                                          # nhiều dòng SUS: báo ở dưới, không tự chọn một dòng
                diem_sus[ma] = sus(r)
            except (ValueError, KeyError):
                canh_bao.append(f"{ma}: phiếu SUS thiếu câu hoặc có điểm ngoài 1–5, không tính")
        theo_nv[r["nhiem_vu"]].append(r)
    for ma, ds in dong_sus.items():
        if len(ds) > 1:
            canh_bao.append(f"{ma}: có phiếu SUS ở {len(ds)} dòng ({', '.join(map(str, ds))}); chỉ được điền ở một dòng, chưa tính")
    if canh_bao:
        print("CẢNH BÁO DỮ LIỆU:")
        for x in canh_bao:
            print("  - " + x)
        print()
    print(f"Số người thử: {len(nguoi)}; số lượt làm nhiệm vụ: {len(rows)}")
    print("\nNhiệm vụ   Hoàn thành   Thời gian trung vị (giây)   Số lần tìm trung vị")
    for nv in sorted(theo_nv):
        ds = theo_nv[nv]
        xong = [r for r in ds if r["hoan_thanh"].strip().lower() in ("co", "có", "1", "x")]
        tg = [float(r["thoi_gian_giay"]) for r in ds if r["thoi_gian_giay"]]
        lan = [float(r["so_lan_tim"]) for r in ds if r["so_lan_tim"]]
        print(f"{nv:<10} {len(xong)}/{len(ds):<10} {statistics.median(tg) if tg else '—':<27} {statistics.median(lan) if lan else '—'}")
    if diem_sus:
        v = list(diem_sus.values())
        print(f"\nSUS: {len(v)} người; trung bình {statistics.mean(v):.1f}; thấp nhất {min(v):.1f}; cao nhất {max(v):.1f}")
        for k in sorted(diem_sus):
            print(f"  {k}: {diem_sus[k]:.1f}")
    print("\nGhi chú lúng túng (nguyên văn):")
    for r in rows:
        if r.get("ghi_chu", "").strip():
            print(f"  {r['ma_nguoi_thu']} {r['nhiem_vu']}: {r['ghi_chu'].strip()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ket_qua_khao_sat_MAU.csv")
