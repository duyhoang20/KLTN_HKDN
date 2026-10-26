import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text, func, or_
from sqlalchemy.orm import Session, defer

from . import models, schemas, search as search_module, tro_ly, quan_tri
from . import mo_hinh_ngon_ngu as llm
from .database import engine, get_db, Base, SessionLocal
from .hieu_truy_van import Y_DINH_TEN, lop_hieu_cau_hoi_bat

# Tạo bảng nếu chưa có. Bảng mới search_logs được tạo tự động ở lần chạy đầu;
# bảng guidance_documents đã có thì KHÔNG bị thay đổi.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hệ thống tra cứu thông minh và trợ lý AI thủ tục hành chính",
    description="Tra cứu BM25 có hiểu câu hỏi tiếng Việt, trợ lý hỏi–đáp có dẫn nguồn, khu vực cán bộ.",
    version="2026.10.24",
)

# Giao diện được chính máy chủ này phục vụ tại http://127.0.0.1:8000/ nên bình
# thường không cần CORS. Mặc định vẫn mở để còn mở được file HTML trực tiếp
# khi phát triển; khi triển khai thật đặt CORS_ORIGINS=https://ten-mien trong .env.
# Khu vực cán bộ dùng mã phiên trong header (không dùng cookie) nên CORS mở
# không tạo ra lỗ hổng giả mạo yêu cầu (CSRF).
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])

# ---- Giới hạn tần suất cho các API công khai (bổ sung 20/10/2026, dùng khi đưa lên mạng) ----
# GIOI_HAN_MOI_PHUT=30 nghĩa là mỗi địa chỉ IP được gọi tối đa 30 lượt/phút vào mỗi nhóm
# API tốn tài nguyên (tra cứu, hỏi trợ lý, đăng nhập cán bộ); gợi ý trong lúc gõ được gấp 3 lần
# vì mỗi lần gõ phím có thể gọi một lượt. Mặc định 0 = tắt, để chạy trên máy cá nhân và bộ
# kiểm thử như cũ.
from collections import defaultdict, deque  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

GIOI_HAN_MOI_PHUT = int(os.getenv("GIOI_HAN_MOI_PHUT", "0") or 0)
_NHOM_GIOI_HAN = {"/api/hoi": "hoi", "/api/tra-cuu": "tra_cuu", "/api/search": "tra_cuu",
                  "/api/goi-y": "goi_y", "/api/quan-tri/dang-nhap": "dang_nhap"}
_LUOT: dict = defaultdict(deque)
_KHOA_LUOT = RLock()


from . import mang  # noqa: E402


def _ip(request: Request) -> str:
    return mang.dia_chi_ip(request)


@app.middleware("http")
async def _gioi_han_tan_suat(request: Request, call_next):
    nhom = _NHOM_GIOI_HAN.get(request.url.path)
    if GIOI_HAN_MOI_PHUT > 0 and nhom:
        bay_gio, khoa = time.monotonic(), (_ip(request), nhom)
        with _KHOA_LUOT:
            q = _LUOT[khoa]
            while q and bay_gio - q[0] > 60:
                q.popleft()
            if len(q) >= GIOI_HAN_MOI_PHUT * (3 if nhom == "goi_y" else 1):
                return JSONResponse({"detail": "Bạn gửi quá nhiều yêu cầu trong một phút. Vui lòng thử lại sau ít phút."},
                                    status_code=429, headers={"Retry-After": "60"})
            q.append(bay_gio)
            if len(_LUOT) > 50000:          # chặn bảng đếm phình to
                _LUOT.clear()
    return await call_next(request)


# ---- Header bảo mật và bộ nhớ đệm cho trang (bổ sung 20/10/2026, bản 2) ----
# Không dùng Content-Security-Policy vì trang dùng script viết liền trong HTML.
_HEADER_AN_TOAN = {
    "X-Content-Type-Options": "nosniff",                 # trình duyệt không đoán sai loại tệp
    "X-Frame-Options": "SAMEORIGIN",                     # trang khác không nhúng được (chống clickjacking)
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def _header_an_toan(request: Request, call_next):
    resp = await call_next(request)
    for k, v in _HEADER_AN_TOAN.items():
        resp.headers.setdefault(k, v)
    p = request.url.path
    if p == "/" or p.endswith(".html") or p == "/quan-tri":
        # Trang HTML luôn hỏi lại máy chủ, để bản cập nhật hiện ra ngay, không cần Ctrl+F5.
        resp.headers["Cache-Control"] = "no-cache"
    return resp
app.include_router(quan_tri.router)

CAP_AP_DUNG = [
    ("ApDungCapXa", "Cấp xã"),
    ("ApDungCapTinh", "Cấp tỉnh"),
    ("ApDungCapBo", "Cấp bộ"),
    ("ApDungCoQuanKhac", "Cơ quan khác"),
    ("ApDungCoQuanNganhDoc", "Cơ quan ngành dọc"),
]
NGUONG_TIN_CAY = tro_ly.NGUONG_TRA_LOI
Q_TOI_DA = 500


def _muc_danh_sach(doc, phan_tram=None, khop=None) -> schemas.MucDanhSach:
    """
    Rút gọn một thủ tục thành dòng hiển thị trong danh sách.
    Các giá trị đều ĐỌC THẲNG từ dữ liệu API, không suy diễn thêm.
    """
    data = doc.data or {}
    cap = [ten for khoa, ten in CAP_AP_DUNG
           if str(data.get(khoa, "")).strip().lower() == "true"]
    return schemas.MucDanhSach(
        id=doc.id,
        procedure_code=doc.procedure_code,
        title=doc.title,
        agency=doc.agency,
        category=doc.category,
        cap_ap_dung=cap,
        trang_thai=(data.get("TrangThai") or None),
        relevance_percent=phan_tram,
        nguon="can_bo" if data.get("NguonDuLieu") == quan_tri.DAU_CAN_BO else "cong_dvc",
        **(khop or {}),
    )


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Kiểm tra API và kết nối DB có hoạt động không."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "message": "Kết nối DB thành công",
            "mo_hinh_ngon_ngu": llm.ten_mo_hinh() if llm.da_bat() else None}


@app.get("/api/guidelines")
def list_guidelines(
    status: str | None = None,
    agency: str | None = None,
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Danh sách thủ tục ĐÃ CÔNG KHAI, có phân trang. Trả về {total, items}.
    Tham số status được giữ cho tương thích nhưng trang công dân chỉ xem được
    bản đã công khai; bản nháp chỉ xem được trong khu vực cán bộ.
    """
    query = db.query(models.GuidanceDocument).filter(models.GuidanceDocument.status == "published")
    if agency:
        query = query.filter(models.GuidanceDocument.agency == agency)
    if category:
        query = query.filter(models.GuidanceDocument.category == category)
    total = query.count()
    rows = (query.order_by(models.GuidanceDocument.id)
            .offset(offset).limit(limit).all())
    return {
        "total": total,
        "items": [_muc_danh_sach(r).model_dump() for r in rows],
    }


@app.get("/api/guidelines/{guideline_id}", response_model=schemas.GuidanceOut)
def get_guideline(guideline_id: int, db: Session = Depends(get_db)):
    doc = db.get(models.GuidanceDocument, guideline_id)
    # Bản nháp / đã lưu trữ không lộ ra trang công dân
    if not doc or doc.status != "published":
        raise HTTPException(status_code=404, detail="Không tìm thấy hướng dẫn")
    return doc


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Số liệu tổng quan hiển thị ở trang chủ."""
    G = models.GuidanceDocument
    q = db.query(G).filter(G.status == "published")
    # Tách hai nguồn (sửa 09/10/2026): thủ tục lấy từ Cổng DVC và hướng dẫn do
    # cán bộ tự soạn (mã nội bộ NB.xxxxxx). Giao diện chỉ gọi phần đầu là
    # "thủ tục từ Cổng Dịch vụ công".
    cong = q.filter(or_(G.procedure_code.is_(None), ~G.procedure_code.like("NB.%")))
    return {
        "total": q.count(),
        "agencies": q.with_entities(G.agency).distinct().count(),
        "categories": q.with_entities(G.category).distinct().count(),
        "cong_dvc": {
            "thu_tuc": cong.count(),
            "co_quan": cong.with_entities(G.agency).distinct().count(),
            "linh_vuc": cong.with_entities(G.category).distinct().count(),
        },
        "huong_dan_can_bo": q.filter(G.procedure_code.like("NB.%")).count(),
        "hieu_cau_hoi": lop_hieu_cau_hoi_bat(),
    }


@app.get("/api/tong-quan")
def tong_quan(db: Session = Depends(get_db)):
    """Số thủ tục theo từng cơ quan và các lĩnh vực nhiều thủ tục nhất (cho trang chủ)."""
    G = models.GuidanceDocument
    cq = (db.query(G.agency, func.count(G.id)).filter(G.status == "published", G.agency.isnot(None))
          .group_by(G.agency).order_by(func.count(G.id).desc()).all())
    lv = (db.query(G.category, func.count(G.id)).filter(G.status == "published", G.category.isnot(None))
          .group_by(G.category).order_by(func.count(G.id).desc()).limit(12).all())
    return {
        "co_quan": [{"ten": a, "so_luong": n} for a, n in cq if a],
        "linh_vuc": [{"ten": c, "so_luong": n} for c, n in lv if c],
        "mo_hinh_ngon_ngu": llm.ten_mo_hinh() if llm.da_bat() else None,
    }


@app.get("/api/filters")
def get_filters(db: Session = Depends(get_db)):
    """
    Trả về dữ liệu cho bộ lọc 2 tầng:
    - agencies: danh sách các cơ quan (Bộ)
    - categories_by_agency: lĩnh vực thuộc từng cơ quan
    - all_categories: tất cả lĩnh vực (dùng khi chọn "Tất cả" cơ quan)
    """
    rows = (
        db.query(models.GuidanceDocument.agency, models.GuidanceDocument.category)
        .filter(models.GuidanceDocument.status == "published")
        .distinct()
        .all()
    )
    agencies = set()
    cats_by_agency = {}
    all_cats = set()
    for agency, category in rows:
        if agency:
            agencies.add(agency)
        if category:
            all_cats.add(category)
        if agency and category:
            cats_by_agency.setdefault(agency, set()).add(category)

    return {
        "agencies": sorted(agencies),
        "categories_by_agency": {a: sorted(c) for a, c in cats_by_agency.items()},
        "all_categories": sorted(all_cats),
    }


@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    """(Giữ để tương thích) Trả về danh sách lĩnh vực."""
    rows = (
        db.query(models.GuidanceDocument.category)
        .filter(models.GuidanceDocument.status == "published")
        .distinct()
        .all()
    )
    cats = sorted({r[0] for r in rows if r[0]})
    return cats


# ---- Bộ nhớ đệm danh sách thủ tục phục vụ tra cứu ----
# Crawler cập nhật qua ORM nên updated_at thay đổi cả khi số bản ghi không đổi.
# Khóa bao trùm việc nạp kho và chấm điểm để chỉ mục toàn cục không bị thay
# giữa hai request. Mỗi process uvicorn có cache/khóa riêng.
_BO_NHO = {"chu_ky": None, "docs": []}
_KHOA_TRA_CUU = RLock()


# Bản ghi GỌN giữ trong bộ nhớ (sửa 20/10/2026 để chạy được trên máy chủ 512 MB RAM).
# Tra cứu chỉ cần mã, tên, cơ quan, lĩnh vực; danh sách kết quả cần thêm vài khóa nhỏ
# trong `data`. Toàn bộ `data` của thủ tục được trợ lý đọc lại từ database khi cần
# (tro_ly.tra_loi(..., nap_day_du=...)). Đo trên kho 9.460 bản ghi: bản cũ giữ cả
# `data` và `search_text` tốn khoảng 400 MB; xem 15_TRIEN_KHAI_LEN_MAY_CHU.md.
_KHOA_GON = ("ApDungCapXa", "ApDungCapTinh", "ApDungCapBo", "ApDungCoQuanKhac", "ApDungCoQuanNganhDoc",
             "TrangThai", "NguonDuLieu")


class _BanGhiGon:
    __slots__ = ("id", "procedure_code", "title", "agency", "category", "status", "data")

    def __init__(self, d):
        self.id, self.procedure_code, self.title = d.id, d.procedure_code, d.title
        self.agency, self.category, self.status = d.agency, d.category, d.status
        goc = d.data or {}
        self.data = {k: goc[k] for k in _KHOA_GON if k in goc}


def _lay_kho(db: Session):
    doc = models.GuidanceDocument
    dem, cap_nhat = (db.query(func.count(doc.id), func.max(doc.updated_at))
                    .filter(doc.status == "published").one())
    chu_ky = (dem, cap_nhat)
    if chu_ky != _BO_NHO["chu_ky"]:
        rows, cuoi = [], 0
        while True:                  # đọc từng lô 500 bản ghi, không giữ bản đầy đủ trong phiên
            lo = (db.query(doc).options(defer(doc.search_text))
                  .filter(doc.status == "published", doc.id > cuoi).order_by(doc.id).limit(500).all())
            if not lo:
                break
            for d in lo:
                rows.append(_BanGhiGon(d))
                db.expunge(d)
            cuoi = lo[-1].id
        # Cần xây lại rõ ràng: search.py tự kiểm tra số lượng, không kiểm tra
        # nội dung. Không thay công thức xếp hạng hoặc bảng tần suất.
        search_module.xay_chi_muc(rows)
        _BO_NHO["docs"] = rows
        _BO_NHO["chu_ky"] = chu_ky
    return _BO_NHO["docs"]


from .an_danh import che_thong_tin_ca_nhan  # noqa: E402  (tách ra 20/10 bản 3)


# Sửa 20/10 bản 3 (F12): nhật ký chỉ giữ NHAT_KY_GIU_NGAY ngày (mặc định 180; 0 = giữ mãi).
# Bản ghi cũ hơn bị xóa khi máy chủ khởi động và tối đa mỗi ngày một lần khi có lượt ghi mới.
NHAT_KY_GIU_NGAY = int(os.getenv("NHAT_KY_GIU_NGAY", "180") or 0)
_DON_NHAT_KY = {"lan_cuoi": 0.0}
_log = logging.getLogger("tra_cuu")


def don_nhat_ky_cu(s: Session) -> int:
    """Xóa nhật ký cũ hơn hạn lưu. Trả về số dòng đã xóa."""
    if NHAT_KY_GIU_NGAY <= 0:
        return 0
    moc = datetime.now(timezone.utc) - timedelta(days=NHAT_KY_GIU_NGAY)
    if s.bind.dialect.name == "sqlite":
        moc = moc.replace(tzinfo=None)
    n = s.query(models.SearchLog).filter(models.SearchLog.created_at < moc).delete(synchronize_session=False)
    s.commit()
    _DON_NHAT_KY["lan_cuoi"] = time.time()
    return n


def _ghi_nhat_ky(kind, query, so_kq, top_pt, top_code, outcome, ms):
    """Ghi nhật ký bằng phiên riêng; lỗi ghi nhật ký không được làm hỏng tra cứu."""
    try:
        s = SessionLocal()
        try:
            if time.time() - _DON_NHAT_KY["lan_cuoi"] > 86400:
                don_nhat_ky_cu(s)
            s.add(models.SearchLog(kind=kind, query=che_thong_tin_ca_nhan(query)[:Q_TOI_DA], result_count=so_kq,
                                   top_percent=top_pt, top_code=top_code, outcome=outcome,
                                   duration_ms=int(round(ms))))
            s.commit()
        finally:
            s.close()
    except Exception:
        pass


# Bổ sung 21/10/2026: lọc kết quả tra cứu theo cấp thực hiện (nhiều thủ tục trùng tên, khác cấp).
CAP_LOC = {"xa": "ApDungCapXa", "tinh": "ApDungCapTinh", "bo": "ApDungCapBo",
           "nganh_doc": "ApDungCoQuanNganhDoc", "khac": "ApDungCoQuanKhac"}


def _xep_hang(q: str, agency, category, kieu: str, db: Session, cap: Optional[str] = None):
    """Lõi tra cứu dùng chung cho /api/search và /api/tra-cuu."""
    q = q.strip()
    # Đặt cả câu trong ngoặc kép = yêu cầu khớp nguyên cụm
    if len(q) >= 2 and q[0] in "\"“”'" and q[-1] in "\"“”'":
        q, kieu = q[1:-1].strip(), "cum"
    if not q:
        return q, [], {"chu_de": "", "tu_dem": [], "dong_nghia": [], "y_dinh": [], "bien_the": []}, kieu
    with _KHOA_TRA_CUU:
        docs = _lay_kho(db)
        # Chấm trên TOÀN kho rồi mới lọc theo cơ quan/lĩnh vực: trọng số của mỗi
        # từ phụ thuộc độ hiếm trong toàn kho, lọc trước sẽ làm thứ hạng đổi
        # theo bộ lọc.
        ranked, pt = search_module.search_chi_tiet(q, docs, limit=max(60, len(docs)))
        if agency:
            ranked = [r for r in ranked if r[0].agency == agency]
        if category:
            ranked = [r for r in ranked if r[0].category == category]
        if cap in CAP_LOC:
            k = CAP_LOC[cap]
            ranked = [r for r in ranked if str((r[0].data or {}).get(k, "")).strip().lower() == "true"]
        out = []
        for doc, _, percent in ranked:
            khop = search_module.kieu_khop(doc, pt["bien_the"])
            if kieu == "cum" and khop["kieu_khop"] not in ("trung_khop", "nguyen_cum"):
                continue
            if kieu == "du_tu" and khop["kieu_khop"] == "mot_phan":
                continue
            out.append((doc, percent, khop))
            if len(out) >= 60:
                break
    return q, out, pt, kieu


@app.get("/api/search", response_model=List[schemas.MucDanhSach])
def search_guidelines(q: str = Query(min_length=1, max_length=2000),
                      category: str | None = None, agency: str | None = None,
                      db: Session = Depends(get_db)):
    """(Giữ để tương thích) Tra cứu, trả về danh sách phẳng. Giao diện mới dùng /api/tra-cuu."""
    _, out, _, _ = _xep_hang(q[:Q_TOI_DA], agency, category, "tat_ca", db)
    return [_muc_danh_sach(doc, percent, khop) for doc, percent, khop in out]


@app.get("/api/tra-cuu")
def tra_cuu(q: str = Query(min_length=1, max_length=Q_TOI_DA),
            category: str | None = None, agency: str | None = None,
            kieu: str = Query(default="tat_ca", pattern="^(tat_ca|du_tu|cum)$"),
            cap: Optional[str] = Query(default=None, pattern="^(xa|tinh|bo|nganh_doc|khac)$"),
            ghi: bool = True,
            db: Session = Depends(get_db)):
    """
    Tra cứu thủ tục theo từ khóa hoặc câu hỏi tự nhiên.

      - Không cần đúng thứ tự từ; gõ có dấu hoặc không dấu đều được.
      - Tự bỏ từ đệm của câu hỏi và đổi cách gọi dân gian sang thuật ngữ hành
        chính (trả về trong trường `hieu` để người dùng thấy hệ thống hiểu gì).
      - kieu = tat_ca | du_tu (tên thủ tục chứa đủ các từ khóa) | cum (khớp
        nguyên cụm). Đặt câu trong ngoặc kép cũng là khớp nguyên cụm.
      - Mỗi kết quả kèm KIỂU KHỚP và số từ khóa khớp, để người dùng không phải
        đoán ý nghĩa của một con số phần trăm.
      - do_tin_cay: cao (kết quả đầu >= 60%), thap (chỉ có gợi ý gần đúng),
        khong (không có kết quả).
    """
    t0 = time.perf_counter()
    q2, out, pt, kieu = _xep_hang(q, agency, category, kieu, db, cap)
    items = [_muc_danh_sach(doc, percent, khop).model_dump() for doc, percent, khop in out]
    top = items[0]["relevance_percent"] if items else None
    tin_cay = "khong" if not items else ("cao" if top >= NGUONG_TIN_CAY else "thap")
    ms = (time.perf_counter() - t0) * 1000
    if ghi:
        _ghi_nhat_ky("tra_cuu", q, len(items), top, items[0]["procedure_code"] if items else None, tin_cay, ms)
    return {
        "truy_van": q2,
        "kieu": kieu,
        "hieu": {
            "chu_de": pt["chu_de"],
            "tu_dem": pt["tu_dem"],
            "dong_nghia": [{"tu": a, "thanh": b} for a, b in pt["dong_nghia"]],
            "y_dinh": [{"ma": y, "ten": Y_DINH_TEN[y]} for y in pt["y_dinh"]],
        },
        "do_tin_cay": tin_cay,
        "tong": len(items),
        "items": items,
        "thoi_gian_ms": round(ms, 1),
    }


@app.get("/api/goi-y")
def goi_y(q: str = Query(min_length=2, max_length=120), db: Session = Depends(get_db)):
    """Gợi ý tên thủ tục trong lúc gõ (tối đa 6 dòng, không ghi nhật ký)."""
    with _KHOA_TRA_CUU:
        docs = _lay_kho(db)
        ranked = search_module.search(q, docs, limit=6)
    xem, out = set(), []
    for doc, _, _ in ranked:
        if doc.title not in xem:
            xem.add(doc.title)
            out.append({"id": doc.id, "title": doc.title, "agency": doc.agency})
    return out


@app.on_event("startup")
def _khoi_dong():
    """Xây chỉ mục tra cứu ngay khi máy chủ khởi động để lượt tra cứu đầu không phải chờ."""
    try:
        s = SessionLocal()
        try:
            with _KHOA_TRA_CUU:
                _lay_kho(s)
            don_nhat_ky_cu(s)
        finally:
            s.close()
    except Exception as e:
        # chưa kết nối được DB: không chặn máy chủ khởi động; ghi lỗi vào log để xem trên máy chủ
        # (sửa 20/10 bản 3, F18). /san-sang sẽ trả 503 cho tới khi kho nạp được.
        _log.error("Khởi động: chưa nạp được kho thủ tục: %s", e)


class CauHoi(BaseModel):
    cau_hoi: str = Field(min_length=2, max_length=Q_TOI_DA)
    id_thu_tuc: Optional[int] = None      # người dùng đã chọn sẵn một thủ tục
    id_ngu_canh: Optional[int] = None     # thủ tục vừa được trả lời ở lượt trước (hội thoại nhiều lượt)
    dung_mo_hinh: bool = True


@app.post("/api/hoi")
def hoi_tro_ly(body: CauHoi, db: Session = Depends(get_db)):
    """
    Trợ lý hỏi–đáp (RAG): truy xuất thủ tục, trích đúng mục dữ liệu theo ý định
    của câu hỏi, trả lời kèm nguồn. Biết hỏi lại khi chưa chắc và từ chối câu
    hỏi ngoài phạm vi. Xem mô tả đầy đủ trong app/tro_ly.py.
    """
    t0 = time.perf_counter()
    chi_dinh = None
    if body.id_thu_tuc is not None:
        chi_dinh = db.get(models.GuidanceDocument, body.id_thu_tuc)
        if not chi_dinh or chi_dinh.status != "published":
            raise HTTPException(404, "Không tìm thấy thủ tục đã chọn")
    # Hội thoại nhiều lượt: câu hỏi tiếp chỉ nêu ý định ("còn lệ phí thì sao")
    # được hiểu là hỏi về thủ tục vừa trả lời ở lượt trước.
    theo_ngu_canh = False
    cau_tra = tro_ly.giao_tiep.boc_loi_chao(body.cau_hoi)[0]
    if (chi_dinh is None and body.id_ngu_canh is not None and not tro_ly.giao_tiep.nhan_dien(body.cau_hoi)
            and tro_ly.phan_tich(cau_tra)["hoi_tiep"]):
        truoc = db.get(models.GuidanceDocument, body.id_ngu_canh)
        if truoc and truoc.status == "published":
            chi_dinh, theo_ngu_canh = truoc, True
    with _KHOA_TRA_CUU:
        docs = _lay_kho(db)
        kq = tro_ly.tra_loi(body.cau_hoi.strip(), docs, doc_chi_dinh=chi_dinh, dung_mo_hinh=False,
                            nap_day_du=lambda d: db.get(models.GuidanceDocument, d.id))
    kq["theo_ngu_canh"] = theo_ngu_canh
    kq["thoi_gian_truy_xuat_ms"] = kq.pop("thoi_gian_ms", None)
    # Mô hình ngôn ngữ (nếu bật) chỉ viết lời dẫn; gọi NGOÀI khóa tra cứu để
    # không chặn người dùng khác trong lúc chờ mô hình.
    if body.dung_mo_hinh and kq["trang_thai"] == "tra_loi":
        doc = chi_dinh or db.get(models.GuidanceDocument, kq["thu_tuc"]["id"])
        t1 = time.perf_counter()
        tro_ly.viet_loi_dan_bang_mo_hinh(kq, doc, body.cau_hoi.strip())
        if kq.get("mo_hinh"):
            kq["thoi_gian_mo_hinh_ms"] = round((time.perf_counter() - t1) * 1000, 1)
    # Thời gian TOÀN BỘ yêu cầu (truy xuất + mô hình), dùng cho nhật ký
    kq["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    tt = kq.get("thu_tuc") or {}
    _ghi_nhat_ky("tro_ly", body.cau_hoi, 1 if tt else len(kq.get("lua_chon") or []),
                 tt.get("do_khop"), tt.get("ma_thu_tuc"), kq["trang_thai"], kq["thoi_gian_ms"])
    return kq


# ---- Kiểm tra sẵn sàng và chẩn đoán (bổ sung 20/10 bản 3) ----
@app.get("/san-sang")
def san_sang(db: Session = Depends(get_db)):
    """Khác /health (chỉ kiểm kết nối): trả 503 nếu database lỗi, kho trống hoặc chưa xây được chỉ mục."""
    try:
        db.execute(text("SELECT 1"))
        with _KHOA_TRA_CUU:
            docs = _lay_kho(db)
    except Exception as e:
        _log.error("Kiểm tra sẵn sàng: %s", e)
        return JSONResponse({"san_sang": False, "ly_do": "Không đọc được database"}, status_code=503)
    if not docs:
        return JSONResponse({"san_sang": False, "ly_do": "Kho chưa có thủ tục công khai nào"}, status_code=503)
    return {"san_sang": True, "so_thu_tuc_cong_khai": len(docs)}


@app.get("/api/quan-tri/kiem-tra-ip", tags=["Khu vực cán bộ"])
def kiem_tra_ip(request: Request, _tk: str = Depends(quan_tri.can_bo)):
    """Cho cán bộ xem máy chủ đang nhận diện IP người gọi ra sao, để đặt SO_PROXY_TIN_CAY đúng."""
    return mang.chan_doan(request)


# Sửa 20/10 bản 3 (F21): đường /api/... không tồn tại trả lỗi 404 dạng JSON như các API khác,
# thay vì rơi xuống trang 404 HTML dành cho người đọc.
@app.api_route("/api/{duong:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_khong_ton_tai(duong: str):
    raise HTTPException(404, "Không có API này")


# ---- Phục vụ giao diện: http://127.0.0.1:8000/ ----
_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND.is_dir():
    @app.get("/quan-tri", include_in_schema=False)
    def trang_quan_tri():
        return FileResponse(_FRONTEND / "quan_tri.html")

    app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")
