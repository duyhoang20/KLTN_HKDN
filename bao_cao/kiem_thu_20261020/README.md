# Kiểm thử kit 20/10/2026 (bản 1–3)

| Tệp / phép đo | Kết quả |
|---|---|
| `API_143.txt` (`kiem_thu_api.py`, bản 3) | 143/143; G13–G17 (bản 1–2) và nhóm I (17 ca hồi quy theo báo cáo kiểm thử độc lập F01–F21) |
| `API_126.txt` (bản 2) | 126/126 |
| `giao_dien_34.txt` (bản 3) | 34/34; thêm D3–D6, F1 |
| `giao_dien_34_tren_ban_cu.txt` | bộ thử bản 3 chạy trên giao diện bản 2: 29/34, năm ca mới trượt, đúng như báo cáo mô tả |
| `CSV_44.txt` | 44/44 |
| `kiem_tra_bo_doi_chieu_ban3.txt` | bộ đối chiếu DC-20261020-1 với 12 kiểu lỗi cố ý |
| `doi_chieu_21_ban3.txt` | đối chiếu 21 thủ tục chi tiết, thêm độ đầy đủ của phần tổng hợp |
| `tro_ly_ban3.txt` | trợ lý 60 câu: 23/29, không đổi |
| `chuyen_du_lieu_PG16.txt` | script chuyển dữ liệu bản 3 trên PostgreSQL 16, 9.461 bản ghi |
| `giao_dien_29.txt` (bản 2) | 29/29 |
| Bộ nhớ máy chủ sau khi nạp kho 9.460 bản ghi (SQLite, dữ liệu chi tiết cỡ thật lặp lại) | 409 MB (bản 16/10) → 215 MB |
| Bộ nhớ máy chủ chạy trên PostgreSQL 16 | khoảng 228 MB |
| `chuyen_du_lieu.py` giữa hai database PostgreSQL 16 | 9.461/9.461 bản ghi, SHA-256 trùng; bộ đếm id đặt lại đúng; chạy lần hai thì dừng |
| Chạy theo cách `Dockerfile` khởi động (PORT=10000, chuỗi `postgres://`) | /health, trang công dân, trang cán bộ, tra cứu, trợ lý hoạt động; lượt 31/phút của cùng IP bị 429, IP khác vẫn 200 |

Chưa dựng thử ảnh Docker và chưa chạy trên Render thật (môi trường kiểm thử không có Docker daemon và tài khoản Render).
