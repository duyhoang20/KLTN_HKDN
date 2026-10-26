# Kiểm thử kit 21/10/2026 (bản 1 và bản 2)

Môi trường: Linux, Python 3.10, SQLite (kho metadata thật 9.451 bản ghi để đo; kho thử giao diện có 21 thủ tục chi tiết). Chưa chạy trên Windows/PostgreSQL 18.

| Tệp | Nội dung |
|---|---|
| `API_154.txt` | **bản 2**: `kiem_thu_api.py` 154/154; thêm I7b (thu hồi phiên sau khởi động lại), I18 (chuyển lịch sử cán bộ, kế hoạch từng bảng); I5, I9 mở rộng |
| `giao_dien_41.txt` | **bản 2**: `kiem_thu_giao_dien.py` 41/41 (Playwright 1.56); thêm D0 (mọi yêu cầu ghi bị chặn), D10 (phản hồi lưu cũ), D11 (xem trước cập nhật) |
| `giao_dien_41_tren_ban_21_10.txt` | bộ thử bản 2 chạy trên giao diện bản 1: 39/41, D10 và D11 trượt đúng như báo cáo đánh giá |
| `kiem_tra_bo_doi_chieu_ban2.txt` | bộ đối chiếu DC-20261021-1, 14 kiểu lỗi cố ý |
| `doi_chieu_21_ban2.txt` | đối chiếu 21 thủ tục: 0/544, 0/505, độ đầy đủ không đổi |
| `chuyen_du_lieu_PG16.txt` | **bản 2**: chuyển dữ liệu trên PostgreSQL 16 (bí danh bị chặn; lịch sử cán bộ đi theo; lỗi ở bảng thứ hai giữ nguyên đích và bộ đếm id) |
| `API_152.txt` | bản 1: 152/152; thêm J1–J5 (hỏi lại), K1–K2 (lịch sử thao tác), L1–L2 (lọc cấp) |
| `giao_dien_38.txt` | bản 1: 38/38 với Playwright 1.56 (bộ chặn URL cũ không chạy trên Playwright 1.55, xem tài liệu 18) |
| `CSV_44.txt` | `test_bo_de.py` 44/44 |
| `hoi_lai_4_bo.txt` | `danh_gia_hoi_lai.py`: bật/tắt quy tắc hỏi lại trên 4 bộ câu hỏi |
| `tro_ly_hoi_lai.txt` | `danh_gia_tro_ly.py` sau khi có quy tắc hỏi lại |
| `anh_tro_ly_hoi_lai.png` | trợ lý hỏi lại với “đăng ký tàu cá cần những gì” |
| `anh_can_bo_xem_truoc.png` | form soạn hướng dẫn có phần xem trước như người dân |
| `anh_can_bo_lich_su_thao_tac.png` | thẻ Lịch sử thao tác (dữ liệu thử) |

Ảnh chụp từ môi trường thử, giờ hiển thị theo múi giờ UTC của máy thử. Ảnh cho báo cáo nên chụp lại trên máy bạn, với dữ liệu thật.
