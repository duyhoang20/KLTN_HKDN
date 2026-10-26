# Kết quả kiểm thử kit 15/10/2026

Môi trường: Linux, Python 3.10, SQLite tách biệt, Chromium (Playwright). Mô hình ngôn ngữ thật tắt; các ca mô hình ngôn ngữ dùng máy chủ giả. **Chưa chạy trên Windows/PostgreSQL.**

| Tệp | Nội dung | Kết quả |
|---|---|---|
| `API_113.txt` | `kiem_thu_api.py` trên bản này | 113/113 |
| `API_113_tren_ban2.txt` | Cùng bộ phép thử, chạy trên mã bản 2 | 108/113: trượt D24, D25, E20, G11, G12, đúng các lỗi bản rà soát độc lập nêu |
| `giao_dien_29.txt` | `kiem_thu_giao_dien.py` trên bản này | 29/29 |
| `giao_dien_29_tren_ban2.txt` | Cùng bộ phép thử, chạy trên bản 2 | 25/29: trượt B9 (14/15 khai báo phông), C5, E5, E6 (ô nhập ra ngoài màn hình, trang cuộn dọc) |
| `CSV_44.txt` | `test_bo_de.py` | 44/44 |
| `kiem_tra_bo_doi_chieu_DC-20261015-1.txt` | Kiểm thử đột biến bộ đối chiếu mới | 100% mọi kiểu, trừ “Miễn lệ phí” 0/470 |
| `kiem_tra_bo_doi_chieu_DC-20261014-2_tren_ban2.txt` | Cùng các kiểu lỗi, chạy với bộ đối chiếu bản 2 | “Thêm dòng: giấy tờ với số bản của giấy tờ khác” 0/25; “Gắn thời hạn của hình thức nộp khác” 1/14 |
| `ABC.txt`, `TN_dev.txt`, `TN_test.txt`, `TN_ngoai.txt`, `tro_ly.txt` | Bộ đo tra cứu và trợ lý | Giống hệt bản 2, chỉ khác thời gian chạy |
| `doi_chieu_21.txt` | Đối chiếu nguồn 21 thủ tục chi tiết | 576/576; 0/544 dòng không căn cứ; 0/544 dòng sai lệch |

Nhãn ba CSV câu hỏi tự nhiên và bộ đánh giá trợ lý chưa được người duyệt. A/B/C dùng ID thủ tục gốc làm đáp án.
