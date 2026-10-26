"""Xác định địa chỉ IP người gọi (tách riêng 20/10 bản 3 để giới hạn tần suất ở main.py và
khóa đăng nhập sai ở quan_tri.py dùng CÙNG một cách tính)."""
import logging
import os

from fastapi import Request

# Sửa 20/10 bản 3 (F11), viết lại 21/10 bản 2 (N08): xác định IP người dùng khi đứng sau proxy.
# Proxy NỐI thêm địa chỉ vào cuối X-Forwarded-For, còn phần đầu danh sách do người gọi tự gửi được,
# nên chỉ tin các mục tính TỪ CUỐI. SO_PROXY_TIN_CAY=N: IP người dùng là mục thứ N tính từ cuối.
#
# N ĐÚNG = số mục trong X-Forwarded-For của một lượt truy cập BÌNH THƯỜNG (trình duyệt không tự
# thêm header) khi nhìn từ ứng dụng. Con số này tùy nền tảng nên PHẢI kiểm trên máy chủ thật:
# đăng nhập cán bộ, mở /api/quan-tri/kiem-tra-ip, xem trường "so_muc" và "goi_y".
#   - N nhỏ hơn số đúng: mọi người dùng bị tính chung IP của proxy (giới hạn thành chung cả trang).
#   - N lớn hơn số đúng: người cố ý tự thêm IP giả vào đầu header có thể lách giới hạn.
# render.yaml đặt 2 theo một trao đổi trên diễn đàn Render (proxy nối thêm cả địa chỉ của nó);
# điều này CHƯA được kiểm chứng.
# Danh sách ngắn hơn N nghĩa là cấu hình không khớp nền tảng: dùng địa chỉ kết nối trực tiếp và
# ghi cảnh báo vào log một lần.
# Chạy trên máy cá nhân: để 0, dùng địa chỉ kết nối trực tiếp.
SO_PROXY_TIN_CAY = int(os.getenv("SO_PROXY_TIN_CAY", "0") or 0)
_log = logging.getLogger("tra_cuu")
_DA_CANH_BAO = {"ngan": False}


def _bo_cong(x: str) -> str:
    """Bỏ số cổng ở cuối một mục X-Forwarded-For (bổ sung 22/10 cho Azure App Service, nơi proxy ghi
    dạng "IP:cổng"). Không bỏ thì mỗi kết nối mới có cổng khác nhau, giới hạn theo IP mất tác dụng.
    "1.2.3.4:5678" -> "1.2.3.4"; "[2001:db8::1]:443" -> "2001:db8::1"; IPv6 không ngoặc giữ nguyên."""
    if x.startswith("[") and "]" in x:
        return x[1:x.index("]")]
    if x.count(":") == 1:
        return x.split(":", 1)[0]
    return x


def _ds_xff(request: Request):
    return [_bo_cong(x.strip()) for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]


def dia_chi_ip(request: Request) -> str:
    ds = _ds_xff(request)
    if SO_PROXY_TIN_CAY > 0 and ds:
        if len(ds) >= SO_PROXY_TIN_CAY:
            return ds[-SO_PROXY_TIN_CAY]
        if not _DA_CANH_BAO["ngan"]:
            _DA_CANH_BAO["ngan"] = True
            _log.warning("X-Forwarded-For có %d mục, ít hơn SO_PROXY_TIN_CAY=%d: kiểm tra lại cấu hình "
                         "bằng /api/quan-tri/kiem-tra-ip", len(ds), SO_PROXY_TIN_CAY)
    return request.client.host if request.client else "?"


def chan_doan(request: Request) -> dict:
    """Thông tin để cán bộ đặt SO_PROXY_TIN_CAY cho đúng nền tảng (mở bằng trình duyệt bình thường)."""
    ds = _ds_xff(request)
    goi_y = (f"Nếu bạn mở trang này bằng trình duyệt bình thường (không tự thêm header), đặt SO_PROXY_TIN_CAY={len(ds)}."
             if ds else "Không có X-Forwarded-For: máy chủ không đứng sau proxy, đặt SO_PROXY_TIN_CAY=0.")
    return {"ip_dung_cho_gioi_han": dia_chi_ip(request), "dia_chi_ket_noi": request.client.host if request.client else None,
            "x_forwarded_for": ds, "so_muc": len(ds), "so_proxy_tin_cay": SO_PROXY_TIN_CAY,
            "khop_cau_hinh": (len(ds) == SO_PROXY_TIN_CAY) if ds else SO_PROXY_TIN_CAY == 0, "goi_y": goi_y}
