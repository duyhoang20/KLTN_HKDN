from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class GuidanceDocument(Base):
    """
    Một thủ tục hành chính.

    Thiết kế: các cột phẳng chỉ để LỌC và TRA CỨU nhanh; toàn bộ nội dung
    chi tiết nằm trong cột `data` dạng JSON. Nhờ vậy mỗi thủ tục có thể có
    tập thông tin khác nhau mà không cần sửa cấu trúc bảng.
    """
    __tablename__ = "guidance_documents"

    id = Column(Integer, primary_key=True, index=True)
    procedure_code = Column(String(50), nullable=True, index=True)

    # Cột phẳng CHỈ để lọc / tra cứu nhanh — giá trị lấy nguyên từ API
    title = Column(Text, nullable=False)
    agency = Column(Text, nullable=True, index=True)
    category = Column(Text, nullable=True, index=True)
    status = Column(String(20), default="published", index=True)

    # Toàn văn phục vụ tra cứu (gộp mọi nội dung có thể tìm kiếm)
    search_text = Column(Text, nullable=True)

    # Toàn bộ dữ liệu chi tiết, giữ nguyên cấu trúc gốc
    data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SearchLog(Base):
    """
    Nhật ký tra cứu (bổ sung 08/10/2026) — phục vụ phân tích nhu cầu người dân:
    câu nào được hỏi nhiều, câu nào hệ thống không trả lời được.
    Chỉ lưu nội dung câu hỏi và số liệu kết quả; KHÔNG lưu địa chỉ IP hay
    thông tin định danh người dùng.
    """
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True)
    kind = Column(String(20), index=True)          # "tra_cuu" | "tro_ly"
    query = Column(Text, nullable=False)
    result_count = Column(Integer, default=0)
    top_percent = Column(Integer, nullable=True)   # độ khớp của kết quả đầu
    top_code = Column(String(50), nullable=True)   # mã thủ tục đứng đầu
    outcome = Column(String(30), nullable=True)    # cao | thap | khong | tra_loi | can_lam_ro | ngoai_pham_vi
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ThaoTacCanBo(Base):
    """
    Nhật ký thao tác của cán bộ (bổ sung 21/10/2026): ai tạo, sửa, công khai, ngừng công khai,
    lưu trữ bản ghi nào, lúc nào. Phục vụ truy vết khi nhiều cán bộ cùng biên tập.
    Bảng MỚI, được tạo tự động ở lần chạy đầu; không thay đổi bảng nào đang có.
    """
    __tablename__ = "thao_tac_can_bo"

    id = Column(Integer, primary_key=True)
    luc = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tai_khoan = Column(String(100), nullable=False)
    hanh_dong = Column(String(30), nullable=False)      # tao | sua | doi_trang_thai | dang_nhap
    id_thu_tuc = Column(Integer, nullable=True, index=True)
    ma_thu_tuc = Column(String(50), nullable=True)
    tieu_de = Column(Text, nullable=True)
    chi_tiet = Column(Text, nullable=True)              # ví dụ: "draft → published"


class PhienThuHoi(Base):
    """
    Mã phiên cán bộ đã đăng xuất (bổ sung 21/10/2026, bản 2). Lưu trong database để mã đã thu hồi
    vẫn bị từ chối sau khi máy chủ khởi động lại hoặc khi chạy nhiều tiến trình. Dòng quá hạn
    (sau thời điểm mã phiên tự hết hạn) được dọn khi có lượt đăng xuất mới.
    Bảng MỚI, được tạo tự động ở lần chạy đầu; không thay đổi bảng nào đang có.
    """
    __tablename__ = "phien_thu_hoi"

    jti = Column(String(32), primary_key=True)
    het_han = Column(Integer, nullable=False, index=True)     # thời điểm mã phiên hết hạn (giây Unix)
