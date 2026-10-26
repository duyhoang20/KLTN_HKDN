"""
Khu vực cán bộ (bổ sung 08/10/2026): đăng nhập, biên tập hướng dẫn, công khai /
ngừng công khai, và thống kê nhật ký tra cứu.

QUY TẮC NGHIỆP VỤ
    - Thủ tục lấy từ Cổng Dịch vụ công (do crawler nạp): cán bộ CHỈ được đổi
      trạng thái công khai. Nội dung không sửa tại đây, để dữ liệu hiển thị
      luôn trùng với nguồn. Muốn nội dung mới thì chạy lại crawler.
    - Hướng dẫn do cán bộ tự soạn: tạo ở trạng thái NHÁP, sửa tự do, công khai
      khi đã duyệt. Bản ghi mang dấu NguonDuLieu = CAN_BO_BIEN_TAP để giao
      diện và trợ lý luôn nói rõ đây không phải dữ liệu của Cổng.
    - Không xóa cứng: "lưu trữ" chỉ đổi trạng thái sang archived.

BẢO MẬT
    - Tài khoản đặt trong backend/.env (QUAN_TRI_TAI_KHOAN, QUAN_TRI_MAT_KHAU).
      Chưa đặt thì toàn bộ khu vực này bị khóa (HTTP 503).
    - Đăng nhập trả về mã phiên có chữ ký HMAC-SHA256 và hạn dùng 8 giờ.
    - So sánh mật khẩu/chữ ký bằng hmac.compare_digest (chống dò theo thời gian).
    - Sai 5 lần trong 5 phút từ CÙNG một địa chỉ IP thì IP đó bị khóa đăng nhập 5 phút
      (sửa 20/10 bản 3: trước đây khóa chung cho mọi người, nên một người gõ sai làm cán bộ
      ở máy khác cũng không đăng nhập được).
    - Đăng xuất thu hồi mã phiên phía máy chủ; đổi tài khoản hoặc mật khẩu trong .env thì
      mọi mã phiên cũ mất hiệu lực (sửa 20/10 bản 3). Từ 21/10 bản 2, mã đã thu hồi được lưu
      trong bảng phien_thu_hoi nên vẫn bị từ chối sau khi khởi động lại. Khóa đăng nhập sai
      vẫn nằm trong bộ nhớ của tiến trình: chạy MỘT tiến trình máy chủ.
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import mang, models
from .database import SessionLocal, get_db

router = APIRouter(prefix="/api/quan-tri", tags=["Khu vực cán bộ"])

HAN_PHIEN = 8 * 3600
TRANG_THAI = ("draft", "published", "archived")
DAU_CAN_BO = "CAN_BO_BIEN_TAP"
_BI_MAT = (os.getenv("BI_MAT_PHIEN") or secrets.token_hex(32)).encode("utf-8")
_SAI: dict = {}                     # ip -> {"lan": [thời điểm sai], "khoa_den": t}
_DA_THU_HOI: dict = {}              # mã phiên (jti) -> hạn, để từ chối mã đã đăng xuất
SAI_TOI_DA, CUA_SO_SAI, THOI_GIAN_KHOA = 5, 300, 300


def _cau_hinh():
    tk, mk = os.getenv("QUAN_TRI_TAI_KHOAN", "").strip(), os.getenv("QUAN_TRI_MAT_KHAU", "")
    if not tk or not mk:
        raise HTTPException(503, "Khu vực cán bộ chưa được bật: hãy đặt QUAN_TRI_TAI_KHOAN và "
                                 "QUAN_TRI_MAT_KHAU trong backend/.env rồi khởi động lại máy chủ.")
    return tk, mk


def _ky(noi_dung: str) -> str:
    # Khóa ký gồm bí mật phiên và tài khoản/mật khẩu hiện hành: đổi mật khẩu thì mã cũ hết hiệu lực.
    tk, mk = _cau_hinh()
    khoa = _BI_MAT + hashlib.sha256(f"{tk}\n{mk}".encode("utf-8")).digest()
    return hmac.new(khoa, noi_dung.encode("utf-8"), hashlib.sha256).hexdigest()


def _tao_phien(tai_khoan: str) -> str:
    het = int(time.time()) + HAN_PHIEN
    than = f"{tai_khoan}|{het}|{secrets.token_hex(8)}"
    return base64.urlsafe_b64encode(f"{than}|{_ky(than)}".encode("utf-8")).decode("ascii")


def _da_thu_hoi_trong_db(jti: str) -> bool:
    """Mã phiên đã bị thu hồi (lưu bền trong database, sửa 21/10 bản 2). Lỗi database → coi như đã thu hồi."""
    try:
        s = SessionLocal()
        try:
            return s.get(models.PhienThuHoi, jti) is not None
        finally:
            s.close()
    except Exception:
        return True


def _doc_phien(authorization: Optional[str]):
    """Trả về (tài khoản, hạn, jti) nếu mã phiên hợp lệ, còn hạn và chưa bị thu hồi; ngược lại None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        tk, het, jti, chu_ky = base64.urlsafe_b64decode(authorization[7:].encode("ascii")).decode("utf-8").rsplit("|", 3)
        if hmac.compare_digest(chu_ky, _ky(f"{tk}|{het}|{jti}")) and int(het) > time.time() \
                and jti not in _DA_THU_HOI and not _da_thu_hoi_trong_db(jti):
            return tk, int(het), jti
    except Exception:
        pass
    return None


def can_bo(authorization: Optional[str] = Header(default=None)) -> str:
    """Dependency: yêu cầu mã phiên hợp lệ, trả về tên tài khoản."""
    _cau_hinh()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Cần đăng nhập")
    p = _doc_phien(authorization)
    if not p:
        raise HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
    return p[0]


class DangNhap(BaseModel):
    tai_khoan: str = Field(max_length=100)
    mat_khau: str = Field(max_length=200)


@router.post("/dang-nhap")
def dang_nhap(body: DangNhap, request: Request):
    tk, mk = _cau_hinh()
    now = time.time()
    ip = mang.dia_chi_ip(request)
    if len(_SAI) > 10000:                                   # chặn bảng đếm phình to
        for k in [k for k, v in _SAI.items() if v["khoa_den"] < now and not v["lan"]]:
            _SAI.pop(k, None)
    ghi = _SAI.setdefault(ip, {"lan": [], "khoa_den": 0.0})
    if now < ghi["khoa_den"]:
        raise HTTPException(429, "Đăng nhập sai quá nhiều lần từ máy này. Vui lòng thử lại sau vài phút.")
    dung = hmac.compare_digest(body.tai_khoan.encode(), tk.encode()) & \
        hmac.compare_digest(body.mat_khau.encode(), mk.encode())
    if not dung:
        ghi["lan"] = [t for t in ghi["lan"] if now - t < CUA_SO_SAI] + [now]
        if len(ghi["lan"]) >= SAI_TOI_DA:
            ghi["khoa_den"], ghi["lan"] = now + THOI_GIAN_KHOA, []
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    _SAI.pop(ip, None)
    try:
        s = SessionLocal()
        try:
            _ghi_thao_tac(s, tk, "dang_nhap")
            s.commit()
        finally:
            s.close()
    except Exception:
        pass                                    # lỗi ghi nhật ký không được chặn đăng nhập
    return {"token": _tao_phien(tk), "tai_khoan": tk, "het_han_sau_giay": HAN_PHIEN}


@router.get("/thao-tac")
def lich_su_thao_tac(gioi_han: int = Query(default=100, ge=1, le=500), id_thu_tuc: Optional[int] = None,
                     db: Session = Depends(get_db), _: str = Depends(can_bo)):
    """Lịch sử thao tác của cán bộ, mới nhất trước (bổ sung 21/10/2026)."""
    t = models.ThaoTacCanBo
    q = db.query(t)
    if id_thu_tuc is not None:
        q = q.filter(t.id_thu_tuc == id_thu_tuc)
    return [{"luc": x.luc.isoformat() if x.luc else None, "tai_khoan": x.tai_khoan, "hanh_dong": x.hanh_dong,
             "id_thu_tuc": x.id_thu_tuc, "ma_thu_tuc": x.ma_thu_tuc, "tieu_de": x.tieu_de, "chi_tiet": x.chi_tiet}
            for x in q.order_by(t.id.desc()).limit(gioi_han)]


@router.post("/dang-xuat")
def dang_xuat(authorization: Optional[str] = Header(default=None)):
    """Thu hồi mã phiên đang dùng (sửa 20/10 bản 3). Mã không hợp lệ thì coi như đã đăng xuất."""
    p = _doc_phien(authorization)
    if p:
        now = time.time()
        for k in [k for k, het in _DA_THU_HOI.items() if het < now]:
            _DA_THU_HOI.pop(k, None)
        _DA_THU_HOI[p[2]] = p[1]
        # Lưu bền vào database để mã vẫn bị từ chối sau khi khởi động lại (sửa 21/10 bản 2).
        s = SessionLocal()
        try:
            s.query(models.PhienThuHoi).filter(models.PhienThuHoi.het_han < int(now)).delete(synchronize_session=False)
            s.merge(models.PhienThuHoi(jti=p[2], het_han=p[1]))
            s.commit()
        finally:
            s.close()
    return {"da_dang_xuat": True}


def _ghi_thao_tac(db: Session, tai_khoan: str, hanh_dong: str, d=None, chi_tiet: str = "") -> None:
    """Ghi một dòng nhật ký thao tác vào CÙNG giao dịch với thay đổi (bổ sung 21/10/2026)."""
    db.add(models.ThaoTacCanBo(tai_khoan=tai_khoan, hanh_dong=hanh_dong,
                               id_thu_tuc=getattr(d, "id", None), ma_thu_tuc=getattr(d, "procedure_code", None),
                               tieu_de=(getattr(d, "title", None) or None), chi_tiet=chi_tiet or None))


def _dong(d: models.GuidanceDocument) -> dict:
    data = d.data or {}
    return {
        "id": d.id, "procedure_code": d.procedure_code, "title": d.title, "agency": d.agency,
        "category": d.category, "status": d.status,
        "nguon": "can_bo" if data.get("NguonDuLieu") == DAU_CAN_BO else "cong_dvc",
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


@router.get("/thu-tuc")
def ds_thu_tuc(q: str = Query(default="", max_length=200), trang_thai: str = "", nguon: str = "",
               limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
               db: Session = Depends(get_db), _: str = Depends(can_bo)):
    G = models.GuidanceDocument
    truy = db.query(G)
    if trang_thai in TRANG_THAI:
        truy = truy.filter(G.status == trang_thai)
    if q.strip():
        k = f"%{q.strip()}%"
        truy = truy.filter(or_(G.title.ilike(k), G.procedure_code.ilike(k)))
    if nguon == "can_bo":
        truy = truy.filter(G.procedure_code.like("NB.%"))
    tong = truy.count()
    rows = truy.order_by(G.updated_at.desc(), G.id.desc()).offset(offset).limit(limit).all()
    return {"total": tong, "items": [_dong(r) for r in rows]}


@router.get("/thu-tuc/{doc_id}")
def xem_thu_tuc(doc_id: int, db: Session = Depends(get_db), _: str = Depends(can_bo)):
    d = db.get(models.GuidanceDocument, doc_id)
    if not d:
        raise HTTPException(404, "Không tìm thấy")
    return dict(_dong(d), data=d.data)


class HuongDan(BaseModel):
    title: str = Field(max_length=500)
    agency: str = Field(default="", max_length=300)
    category: str = Field(default="", max_length=300)
    noi_dung: str = Field(max_length=20000)

    # Kiểm tra độ dài SAU khi bỏ khoảng trắng: chuỗi toàn dấu cách không được
    # coi là có nội dung (sửa 09/10/2026).
    @field_validator("title", "agency", "category", "noi_dung")
    @classmethod
    def _bo_khoang_trang(cls, v: str) -> str:
        return " ".join(v.split()) if "\n" not in v else "\n".join(x.rstrip() for x in v.strip().splitlines())

    @field_validator("title")
    @classmethod
    def _ten_du_dai(cls, v: str) -> str:
        if len(v) < 5:
            raise ValueError("Tên hướng dẫn phải có ít nhất 5 ký tự (không tính khoảng trắng)")
        return v

    @field_validator("noi_dung")
    @classmethod
    def _noi_dung_du_dai(cls, v: str) -> str:
        if len("".join(v.split())) < 10:
            raise ValueError("Nội dung phải có ít nhất 10 ký tự (không tính khoảng trắng)")
        return v


def _data_can_bo(body: HuongDan, nguoi: str) -> dict:
    return {
        "NguonDuLieu": DAU_CAN_BO,
        "TenThuTuc": body.title.strip(),
        "CoQuanBanHanh": {"TenCoQuanBanHanh": body.agency.strip()},
        "LinhVuc": {"TenLinhVuc": body.category.strip()},
        "NoiDungHuongDan": body.noi_dung.strip(),
        "NguoiBienTap": nguoi,
    }


@router.post("/thu-tuc", status_code=201)
def tao_huong_dan(body: HuongDan, db: Session = Depends(get_db), nguoi: str = Depends(can_bo)):
    d = models.GuidanceDocument(
        title=body.title.strip(), agency=body.agency.strip() or None,
        category=body.category.strip() or None, status="draft",
        search_text=body.noi_dung.strip(), data=_data_can_bo(body, nguoi))
    db.add(d)
    db.flush()
    d.procedure_code = f"NB.{d.id:06d}"          # mã nội bộ, phân biệt với mã của Cổng DVC
    d.data = dict(d.data, MaThuTucHanhChinh=d.procedure_code)
    _ghi_thao_tac(db, nguoi, "tao", d, "tạo bản nháp")
    db.commit()
    return _dong(d)


@router.put("/thu-tuc/{doc_id}")
def sua_huong_dan(doc_id: int, body: HuongDan, db: Session = Depends(get_db), nguoi: str = Depends(can_bo)):
    d = db.get(models.GuidanceDocument, doc_id)
    if not d:
        raise HTTPException(404, "Không tìm thấy")
    if (d.data or {}).get("NguonDuLieu") != DAU_CAN_BO:
        raise HTTPException(409, "Thủ tục lấy từ Cổng Dịch vụ công không sửa nội dung tại đây "
                                 "(để dữ liệu luôn trùng với nguồn). Chỉ có thể đổi trạng thái công khai.")
    d.title, d.agency, d.category = body.title.strip(), body.agency.strip() or None, body.category.strip() or None
    d.search_text = body.noi_dung.strip()
    d.data = dict(_data_can_bo(body, nguoi), MaThuTucHanhChinh=d.procedure_code)
    # Sửa một bản ĐANG CÔNG KHAI thì bản đó trở về NHÁP và rời khỏi trang công
    # dân cho tới khi được công khai lại (duyệt rồi mới công khai). Trước
    # 09/10/2026, nội dung sửa hiện ngay cho người dân mà chưa qua duyệt.
    ve_nhap = d.status == "published"
    if ve_nhap:
        d.status = "draft"
    _ghi_thao_tac(db, nguoi, "sua", d, "sửa nội dung" + ("; chuyển từ công khai về nháp" if ve_nhap else ""))
    db.commit()
    return dict(_dong(d), da_chuyen_ve_nhap=ve_nhap)


class DoiTrangThai(BaseModel):
    status: str


@router.post("/thu-tuc/{doc_id}/trang-thai")
def doi_trang_thai(doc_id: int, body: DoiTrangThai, db: Session = Depends(get_db), nguoi: str = Depends(can_bo)):
    if body.status not in TRANG_THAI:
        raise HTTPException(422, f"Trạng thái phải là một trong {TRANG_THAI}")
    d = db.get(models.GuidanceDocument, doc_id)
    if not d:
        raise HTTPException(404, "Không tìm thấy")
    cu = d.status
    d.status = body.status
    d.updated_at = func.now()        # bảo đảm bộ nhớ đệm tra cứu nhận thay đổi
    if cu != body.status:
        _ghi_thao_tac(db, nguoi, "doi_trang_thai", d, f"{cu} → {body.status}")
    db.commit()
    db.refresh(d)
    return _dong(d)


@router.get("/tong-quan")
def tong_quan(db: Session = Depends(get_db), _: str = Depends(can_bo)):
    """Số liệu kho dữ liệu và các phép kiểm tra chất lượng dữ liệu."""
    G = models.GuidanceDocument
    theo_tt = dict(db.query(G.status, func.count(G.id)).group_by(G.status).all())
    theo_cq = (db.query(G.agency, func.count(G.id)).filter(G.status == "published")
               .group_by(G.agency).order_by(func.count(G.id).desc()).all())
    ma_trung = (db.query(G.procedure_code, func.count(G.id)).filter(G.procedure_code.isnot(None))
                .group_by(G.procedure_code).having(func.count(G.id) > 1).count())
    ten_trung = (db.query(G.title).filter(G.status == "published")
                 .group_by(G.title).having(func.count(G.id) > 1).count())
    return {
        "theo_trang_thai": {k or "": v for k, v in theo_tt.items()},
        "theo_co_quan": [{"co_quan": a or "(không ghi)", "so_luong": n} for a, n in theo_cq],
        "chat_luong": {
            "ma_thu_tuc_trung": ma_trung,
            "ten_thu_tuc_trung": ten_trung,
            "thieu_ma": db.query(G).filter(G.procedure_code.is_(None)).count(),
            "thieu_linh_vuc": db.query(G).filter(or_(G.category.is_(None), G.category == "")).count(),
            "thieu_co_quan": db.query(G).filter(or_(G.agency.is_(None), G.agency == "")).count(),
        },
    }


GIOI_HAN_NHAT_KY = 20000


@router.get("/nhat-ky")
def nhat_ky(ngay: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db), _: str = Depends(can_bo)):
    """Phân tích nhật ký tra cứu trong `ngay` ngày gần nhất."""
    L = models.SearchLog
    # Đọc tối đa GIOI_HAN_NHAT_KY lượt mới nhất rồi lọc theo thời gian. Sửa 14/10: nếu
    # giới hạn này cắt mất một phần khoảng thời gian được hỏi thì báo rõ (da_cat),
    # để số thống kê không bị hiểu là của toàn bộ khoảng thời gian.
    rows = db.query(L).order_by(L.id.desc()).limit(GIOI_HAN_NHAT_KY + 1).all()
    moc = time.time() - ngay * 86400
    da_cat = len(rows) > GIOI_HAN_NHAT_KY
    rows = rows[:GIOI_HAN_NHAT_KY]
    if da_cat and rows and rows[-1].created_at is not None and rows[-1].created_at.timestamp() < moc:
        da_cat = False          # lượt cũ nhất đọc được đã nằm ngoài khoảng: không thiếu gì
    rows = [r for r in rows if r.created_at is None or r.created_at.timestamp() >= moc]

    def chuan(s):
        return " ".join((s or "").lower().split())

    tat_ca = Counter(chuan(r.query) for r in rows)
    rong = Counter(chuan(r.query) for r in rows if r.outcome in ("khong", "ngoai_pham_vi"))
    yeu = Counter(chuan(r.query) for r in rows if r.outcome in ("thap", "can_lam_ro"))
    theo_ngay = Counter(r.created_at.strftime("%Y-%m-%d") for r in rows if r.created_at)
    tg = sorted(r.duration_ms for r in rows if r.duration_ms is not None)
    n = len(rows)
    return {
        "so_ngay": ngay,
        "gioi_han": GIOI_HAN_NHAT_KY,
        "da_cat": da_cat,
        "tong_luot": n,
        "luot_tra_cuu": sum(1 for r in rows if r.kind == "tra_cuu"),
        "luot_hoi_tro_ly": sum(1 for r in rows if r.kind == "tro_ly"),
        "ti_le_khong_ket_qua": round(100 * sum(rong.values()) / n, 1) if n else 0,
        "ti_le_do_khop_thap": round(100 * sum(yeu.values()) / n, 1) if n else 0,
        "thoi_gian_trung_vi_ms": tg[len(tg) // 2] if tg else None,
        "thoi_gian_p95_ms": tg[min(len(tg) - 1, int(len(tg) * 0.95))] if tg else None,
        "hoi_nhieu_nhat": [{"cau": c, "so_lan": k} for c, k in tat_ca.most_common(15)],
        "khong_co_ket_qua": [{"cau": c, "so_lan": k} for c, k in rong.most_common(15)],
        "do_khop_thap": [{"cau": c, "so_lan": k} for c, k in yeu.most_common(15)],
        "theo_ngay": [{"ngay": d, "so_luot": k} for d, k in sorted(theo_ngay.items())[-30:]],
        "gan_day": [{"luc": r.created_at.isoformat() if r.created_at else None, "loai": r.kind,
                     "cau": r.query, "so_ket_qua": r.result_count, "ket_cuc": r.outcome,
                     "ms": r.duration_ms} for r in rows[:30]],
    }
