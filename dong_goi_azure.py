"""Đóng gói mã nguồn để đưa lên Azure App Service (bổ sung 22/10/2026).

Dùng (ở thư mục gốc của kho mã, cùng chỗ với tệp này):
    python dong_goi_azure.py

Tạo tệp azure_deploy.zip chỉ gồm những gì máy chủ cần:
    requirements.txt            (trỏ tới backend/requirements.txt; Azure chỉ tìm tệp này ở thư mục gốc)
    backend/requirements.txt
    backend/app/...             (mã máy chủ)
    frontend/...                (trang công dân, trang cán bộ, phông chữ)

KHÔNG bao giờ đưa vào: backend/.env (mật khẩu database, tài khoản API), venv, __pycache__,
database, bộ đề, báo cáo. Sau khi tạo, script tự mở lại tệp zip để kiểm tra điều này.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

GOC = Path(__file__).resolve().parent
RA = GOC / "azure_deploy.zip"
LAY = [GOC / "requirements.txt", GOC / "backend" / "requirements.txt", GOC / "backend" / "app", GOC / "frontend"]
BO_THU_MUC = {"__pycache__", "venv", ".venv", "node_modules", ".git"}
BO_DUOI = {".pyc", ".pyo", ".db", ".sqlite", ".log", ".zip"}
CAM = (".env",)          # tên tệp tuyệt đối không được nằm trong gói


def cac_tep():
    for muc in LAY:
        if not muc.exists():
            sys.exit(f"Thiếu {muc.relative_to(GOC)}: hãy chạy script ở thư mục gốc của kho mã (nơi có README.md).")
        ds = [muc] if muc.is_file() else sorted(p for p in muc.rglob("*") if p.is_file())
        for p in ds:
            rel = p.relative_to(GOC)
            if any(phan in BO_THU_MUC for phan in rel.parts) or p.suffix.lower() in BO_DUOI:
                continue
            if p.name.startswith(CAM):
                continue
            yield p, rel.as_posix()


def main():
    so = 0
    with zipfile.ZipFile(RA, "w", zipfile.ZIP_DEFLATED) as z:
        for p, ten in cac_tep():
            z.write(p, ten)
            so += 1
    with zipfile.ZipFile(RA) as z:
        ten_trong_goi = z.namelist()
    lo = [t for t in ten_trong_goi if Path(t).name.startswith(CAM)]
    if lo:
        RA.unlink()
        sys.exit("DỪNG: gói có tệp cấu hình chứa mật khẩu (" + ", ".join(lo) + "). Đã xóa gói.")
    for bat_buoc in ("requirements.txt", "backend/app/main.py", "frontend/index.html", "frontend/quan_tri.html"):
        if bat_buoc not in ten_trong_goi:
            sys.exit(f"DỪNG: gói thiếu {bat_buoc}.")
    sha = hashlib.sha256(RA.read_bytes()).hexdigest()
    print(f"Đã tạo {RA.name}: {so} tệp, {RA.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"SHA-256: {sha}")
    print("Đã kiểm: không có .env, không có venv, có đủ backend/app và frontend.")


if __name__ == "__main__":
    main()
