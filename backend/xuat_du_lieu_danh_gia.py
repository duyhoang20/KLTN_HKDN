"""Xuất kho tra cứu thật để tái lập phép đo A/B/C ở máy khác.

Chạy từ backend, dùng venv và cấu hình DB hiện có:
    python xuat_du_lieu_danh_gia.py --bao-cao bao_cao_nen_ABC_500.txt

Chỉ SELECT trong giao dịch PostgreSQL READ ONLY; không tạo/sửa/xóa bảng.
Chỉ xuất id, procedure_code, title, category, status, agency.
Không xuất .env, tài khoản, mật khẩu, token, search_text hoặc nội dung data.
Chỉ tạo JSON khi dấu kiểm tra kho, bộ đo và search.py khớp báo cáo nền.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


THU_MUC = Path(__file__).resolve().parent
TRUONG_BAM = ("id", "procedure_code", "title", "category", "status")


def sha_json(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha_file(path):
    return hashlib.sha256(
        Path(path).read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()


def doc_ma_bao_cao(noi_dung, nhan):
    pattern = r"^" + re.escape(nhan) + r"\s*:\s*([a-fA-F0-9]{64})\s*$"
    found = re.search(pattern, noi_dung, flags=re.MULTILINE)
    if not found:
        raise ValueError(f"Báo cáo thiếu dấu kiểm tra: {nhan}")
    return found.group(1).lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bao-cao", required=True, type=Path)
    parser.add_argument("--luu", type=Path, default=Path("du_lieu_danh_gia.json"))
    args = parser.parse_args()
    if args.luu.suffix.lower() != ".json":
        parser.error("File xuất phải có đuôi .json.")
    if args.luu.exists():
        parser.error("File xuất đã tồn tại. Dùng --luu với tên .json khác.")

    try:
        bao_cao = args.bao_cao.read_text(encoding="utf-8-sig")
        ma_kho_nen = doc_ma_bao_cao(bao_cao, "SHA256 kho tra cứu")
        ma_bo_do = doc_ma_bao_cao(bao_cao, "SHA256 bộ đo")
        ma_search = doc_ma_bao_cao(bao_cao, "SHA256 search.py")
        if sha_file(THU_MUC / "danh_gia.py") != ma_bo_do:
            raise ValueError("danh_gia.py không khớp báo cáo nền.")
        if sha_file(THU_MUC / "app" / "search.py") != ma_search:
            raise ValueError("app/search.py không khớp báo cáo nền.")
    except (OSError, ValueError) as exc:
        print(f"Không xuất dữ liệu: {exc}")
        return 1

    sys.path.insert(0, str(THU_MUC))
    from sqlalchemy import text
    from app.database import SessionLocal
    from app.models import GuidanceDocument as Doc

    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        rows = (db.query(Doc.id, Doc.procedure_code, Doc.title,
                         Doc.category, Doc.status, Doc.agency)
                .filter(Doc.status == "published")
                .order_by(Doc.id).all())
        documents = [dict(row._mapping) for row in rows]
    finally:
        db.close()

    ma_kho = sha_json([[doc[k] for k in TRUONG_BAM] for doc in documents])
    if ma_kho != ma_kho_nen:
        print("Không xuất: kho hiện tại khác kho dùng trong báo cáo nền.")
        print(f"Báo cáo: {ma_kho_nen}")
        print(f"Hiện tại: {ma_kho}")
        print("Gửi thông báo này để kiểm tra trước khi đo lại.")
        return 1

    payload = {
        "format_version": 1,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(documents),
        "sha256_corpus": ma_kho,
        "sha256_evaluator": ma_bo_do,
        "sha256_search": ma_search,
        "fingerprint_fields": list(TRUONG_BAM),
        "documents": documents,
    }
    with args.luu.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(f"Đã xuất {len(documents)} thủ tục; dấu kiểm tra KHỚP báo cáo nền.")
    print(f"File: {args.luu.resolve()}")
    print("Gửi file JSON này cùng báo cáo nền để tái lập đánh giá.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
