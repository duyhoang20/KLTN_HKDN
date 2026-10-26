from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict


class MucDanhSach(BaseModel):
    """
    Một dòng trong danh sách kết quả — chỉ gồm thông tin cần để hiển thị.
    Không kèm dữ liệu chi tiết, vì một thủ tục có thể có hàng chục khoản phí
    và hàng chục giấy tờ; trả hết cho 20-60 dòng là lãng phí.
    """
    id: int
    procedure_code: Optional[str] = None
    title: str
    agency: Optional[str] = None
    category: Optional[str] = None
    # Đọc trực tiếp từ dữ liệu API, không suy diễn thêm
    cap_ap_dung: List[str] = []
    trang_thai: Optional[str] = None
    relevance_percent: Optional[int] = None
    # Nguồn bản ghi: cong_dvc (Cổng Dịch vụ công) | can_bo (cán bộ biên soạn)
    nguon: str = "cong_dvc"
    # Kiểu khớp minh bạch (chỉ có khi tra cứu): trung_khop | nguyen_cum | du_tu | mot_phan
    kieu_khop: Optional[str] = None
    so_tu_khop: Optional[int] = None
    so_tu: Optional[int] = None
    ti_le_tu: Optional[int] = None


class GuidanceOut(BaseModel):
    """Chi tiết một thủ tục: kèm toàn bộ khối dữ liệu gốc."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    procedure_code: Optional[str] = None
    title: str
    agency: Optional[str] = None
    category: Optional[str] = None
    status: str
    data: Optional[Dict[str, Any]] = None
