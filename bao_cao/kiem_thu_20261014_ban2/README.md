# Kết quả kiểm thử và đo đợt 14/10/2026 (bản 2)

Môi trường: Linux, Python 3.10 với đúng `requirements.txt`, SQLite tách biệt (kiểu JSONB thay bằng JSON chỉ trong tiến trình thử), Chromium cho kiểm thử giao diện. Không dùng PostgreSQL, Windows hay mô hình ngôn ngữ thật. Những kết quả này **không thay** kết quả chạy trên máy của bạn.

| Tệp | Nội dung | Kết quả |
|---|---|---|
| `API_107.txt` | `kiem_thu_api.py`: 93 phép cũ cộng 14 phép mới (D20–D23, E13–E19, G8–G10) | 107/107 |
| `CSV_44.txt` | `test_bo_de.py` | 44/44 |
| `giao_dien_25.txt` | `kiem_thu_giao_dien.py`, chạy được trên máy bạn | 25/25 |
| `kiem_tra_bo_doi_chieu_ban_chat.txt` | lỗi cố ý đưa vào bộ đối chiếu bản chặt DC-20261014-2 | 6/7 kiểu lỗi bắt được 100%; “Miễn lệ phí” 0% (giới hạn đã ghi) |
| `kiem_tra_bo_doi_chieu_ban_cu_0910.txt` | cùng phép thử trên bộ đối chiếu cũ (có trong kit 14/10) | sai đơn vị thời gian 6,9%; sai tiền tệ 5,5%; sai số tiền 33,3%; sai số bản 0% |
| `ABC.txt`, `TN_dev.txt`, `TN_test.txt`, `TN_ngoai.txt` | bộ đo tra cứu | giống bản 14/10 (bỏ qua dòng thời gian chạy) |
| `tro_ly.txt` | bộ đo trợ lý TL-20261014-1 | 23/29 trả lời thẳng đúng thủ tục, không đổi |
| `doi_chieu_21.txt` | đối chiếu nguồn 21 thủ tục, bản chặt | 576/576 dữ kiện; 0/544 dòng không căn cứ; 0/544 dòng sai lệch số–đơn vị |

Thuật toán tra cứu (`search.py`, SHA256 `fd78194b…`), bảng đồng nghĩa, ngưỡng và parser không đổi, nên các số tra cứu giống hệt. Thay đổi backend chỉ nằm ở bốn chỗ: lời dẫn mô hình ngôn ngữ (chỉ chạy khi bật mô hình), bộ đối chiếu nguồn (công cụ đo), cờ giới hạn nhật ký và che thông tin cá nhân trong nhật ký.
