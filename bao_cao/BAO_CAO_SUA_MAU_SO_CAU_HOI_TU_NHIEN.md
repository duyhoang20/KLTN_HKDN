> **ĐÃ HOÀN TÁC NGÀY 29/09/2026 — không còn áp dụng.** Bản sửa mẫu số trong tài liệu này làm truy vấn ngoài phạm vi nhận kết quả sai tới 100% (kiểm thử độc lập 29/09, `bao_cao/BAO_CAO_KIEM_THU_20260929.md`). Lý do gốc: từ nội dung không có trong kho ("phở", "iPhone") là dấu hiệu câu ngoài phạm vi, không phải từ đệm vô nghĩa. Tài liệu này có hai chỗ ghi sai: ví dụ "kết hôn với người nước ngoài" thực tế có 11 kết quả và đầu bảng là thủ tục khác; "4 bộ đề, 3.500 truy vấn" đúng ra là 7 bộ × 500 = 3.500 truy vấn. Các khẳng định "không câu nào xấu đi" chỉ đúng trên bộ 50 câu trong phạm vi. Giữ lại để truy vết; xem `05_THAY_DOI_20260929.md`.

# Báo cáo cải tiến: câu hỏi tự nhiên bị trả về rỗng — 28/09/2026

## 1. Kết luận

Sửa cách tính **mẫu số phần trăm** trong `search.py`: chỉ tính các đơn vị truy vấn có xuất hiện trong kho. Điểm xếp hạng, tập ứng viên, công thức BM25, hệ số và ngưỡng giữ nguyên.

Trên 50 câu hỏi tự nhiên, số câu trả về rỗng giảm từ **7 xuống 0**. Theo phép đo xấp xỉ (mục 5), 9 câu có kết quả liên quan lên hạng tốt hơn, **không câu nào xấu đi**. Trên bộ đo chính ABC-20260924-1 và 4 bộ đề kiểm tra thêm (3.500 truy vấn), **thứ hạng đáp án giống hệt bản trước từng truy vấn**.

Đây là sửa lỗi quy đổi phần trăm, không phải cải tiến khả năng hiểu nghĩa: truy vấn dùng từ đồng nghĩa (ví dụ "sổ đỏ") vẫn chưa tìm đúng.

## 2. Vấn đề

Tìm "làm hộ chiếu cần những gì" trả về 0 kết quả, trong khi "cấp hộ chiếu" trả về 14. Bộ đo A/B/C không phát hiện được vì truy vấn của nó cắt từ chính tên thủ tục, không bao giờ có từ đệm.

Phân tích truy vấn trên kho 9.451 thủ tục:

| Đơn vị truy vấn | Số thủ tục chứa | Trọng số |
|---|---:|---:|
| cần những, chiếu cần, làm hộ, những gì | 0 | 24,62 mỗi đơn vị |
| hộ chiếu | 27 | 10,53 |
| chiếu | 43 | 5,38 |
| cần / làm / hộ | 231 / 665 / 904 | 3,71 / 2,65 / 2,35 |

Phần trăm = điểm BM25 ÷ điểm của một tài liệu giả định khớp mọi đơn vị. Bốn cặp ghép từ từ đệm không có trong thủ tục nào nên IDF đạt tối đa và chiếm **80% mẫu số**. Không tài liệu nào khớp được chúng, nên điểm tối đa thực tế chỉ khoảng 20% — luôn dưới ngưỡng 40% (kết quả chính) và thường dưới 25% (gợi ý), dẫn đến trả về rỗng.

## 3. Thay đổi

```python
def _co_trong_kho(term):
    return _IDX["df"].get(normalize(term), 0) > 0

# trong chuan_bi_truy_van():
"toi_da": sum(v * mau_chuan for t, v in w.items() if _co_trong_kho(t)) or 1.0,
```

Lý do đúng về mặt nguyên lý: một đơn vị không xuất hiện trong kho góp 0 điểm cho **mọi** tài liệu, nên nó không phân biệt được tài liệu nào với tài liệu nào; đưa nó vào mẫu số chỉ làm méo thang phần trăm.

**Phiên bản thử đầu tiên đã bị loại.** Bản đầu bỏ các đơn vị này khỏi cả trọng số chấm điểm. Kiểm tra trên 500 truy vấn có dấu cho thấy 1 câu lên hạng và 1 câu xuống hạng. Nguyên nhân: `STOPWORDS` chỉ lưu dạng không dấu, nên nhánh có dấu vẫn chấm "về", "hoặc", "một", "tại"; bản đầu vô tình loại chúng khỏi nhánh này. Đó là vấn đề tồn đọng số 3 (bất nhất stopwords), cần đánh giá riêng, nên bản bàn giao thu hẹp lại chỉ sửa mẫu số.

## 4. Bộ đo chính và các bộ đề kiểm tra thêm

Cùng kho (SHA256 `2319b44b…f8de685`), cùng bộ đo ABC-20260924-1:

| Bộ đề | Trước | Sau | Thứ hạng đáp án |
|---|---|---|---|
| A, seed gốc, 500 câu | Top-1 90,8% | 90,8% | báo cáo giống từng byte (trừ dòng SHA search.py) |
| B, seed gốc, 500 câu | Top-1 72,0% | 72,0% | như trên |
| C, seed gốc, 500 câu | Top-1 21,6% | 21,6% | như trên |
| A, seed 777 / 31337 / 424242 | 92,0 / 90,4 / 92,0% | không đổi | giống hệt từng truy vấn |
| B, seed 777 / 31337 / 424242 | 70,4 / 73,8 / 70,0% | không đổi | giống hệt từng truy vấn |
| B có dấu, seed 5555, 500 câu | 74,2% | 74,2% | giống hệt từng truy vấn |

Chạy lại bộ đo câu hỏi tự nhiên với `PYTHONHASHSEED` khác cho báo cáo giống từng byte.

## 5. Bộ câu hỏi tự nhiên (50 câu, chưa gán nhãn)

Bộ đề mới nằm ở `bo_de_tu_nhien/`, chưa có nhãn đáp án do người gán. Hai phép đo dưới đây vì vậy chỉ mang tính **tham khảo**, không thay cho chỉ số trên nhãn thật.

**Không cần nhãn** — tỉ lệ trả về rỗng (bộ đo TN-20260928-1):

| Loại câu | Trước | Sau |
|---|---:|---:|
| Câu hỏi đời thường (37) | 5 | 0 |
| Từ đồng nghĩa / thuật ngữ cũ (9) | 2 | 0 |
| Gõ không dấu (4) | 0 | 0 |
| Tổng (50) | 7 (14%) | 0 |

**Xấp xỉ** — coi thủ tục có tên chứa khái niệm cần tìm của câu hỏi (cột khái niệm trong `ung_vien_goi_y.txt`) là liên quan:

| | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| Trước | 70,0% | 72,0% | 0,711 |
| Sau | 78,0% | 84,0% | 0,808 |

Hạng của kết quả liên quan đầu tiên: 9 câu tốt lên, 0 câu xấu đi. Ví dụ: "tôi muốn đăng ký tạm trú cho người thuê trọ" từ rỗng thành "Đăng ký tạm trú" đứng đầu; "thủ tục đăng ký kết hôn với người nước ngoài như thế nào" từ 1 kết quả thành 10, đứng đầu "Thủ tục đăng ký kết hôn có yếu tố nước ngoài".

## 6. Giới hạn và tác dụng phụ

**Chưa sửa khoảng trống đồng nghĩa.** "xin cấp sổ đỏ lần đầu" trước và sau đều không có thủ tục quyền sử dụng đất nào trong kết quả; "xin visa" chưa ra thủ tục thị thực.

**Kết quả sai hiện với phần trăm cao hơn.** Với các câu không có thủ tục khớp đúng, kết quả trước đây chỉ hiện dạng gợi ý (~31%) nay có thể hiện như kết quả chính (~51%). Ví dụ "sổ đỏ" ở trên. Người dùng có thể tin nhầm hơn.

**Kết quả liên quan chưa chắc lên đầu.** "xin giấy phép kinh doanh karaoke": trước trả 2 kết quả đều về hàng không, không có thủ tục karaoke nào; sau có thủ tục karaoke ở hạng 4, 5, 7, 9, nhưng đầu bảng vẫn là giấy phép vận chuyển hàng không vì tên thủ tục đó lặp "giấy phép kinh doanh" hai lần (ảnh hưởng tham số k1, xem mục 7).

**Nhiều kết quả hơn.** Một số câu tăng từ vài kết quả lên 60. Số kết quả nhiều hơn không đồng nghĩa với tốt hơn.

**Không bảo đảm mọi truy vấn không xấu đi.** Thứ tự điểm không đổi, nhưng phần trăm thay đổi nên tập kết quả qua ngưỡng có thể khác. Về lý thuyết, một kết quả trước đây nằm trong 8 gợi ý có thể bị loại khi xuất hiện kết quả vượt 40%. Không quan sát thấy trường hợp này trong các phép đo trên, nhưng không loại trừ.

## 7. Quan sát ngoài phạm vi thay đổi (chưa sửa)

Tìm "đăng ký hộ khẩu", thủ tục "Đăng ký cập nhật… hộ kinh doanh" đứng hạng 4 (99%) trên cả "Cấp đổi sổ hộ khẩu", vì tên lặp "đăng ký hộ" ba lần và BM25 thưởng cho tần suất. Phần trăm cũng dồn gần 100% (100, 99, 99, 99, 98) nên ít giá trị phân biệt. Thử giảm k1 (1,5 → 1,2 / 0,9 / 0,6 / 0,3): thủ tục lạc đề tụt xuống hạng 10–12, nhưng bộ A/B gần như không đổi (B giảm đúng 1 truy vấn ở mọi mức). Theo quy tắc không giảm B, **chưa đổi k1**. Bộ A/B không đo được loại lỗi "lạc đề" này; cần bộ câu hỏi tự nhiên có nhãn để quyết định.

## 8. Phương pháp và tái lập

Kho: 9.451 bản ghi thật từ `kiem_chung_tra_cuu.zip` (bản xuất 24/09), nạp vào SQLite tạm qua đúng model của dự án (thay JSONB bằng JSON trong tiến trình kiểm thử). Chạy nguyên văn `danh_gia.py` và `danh_gia_tu_nhien.py` trong gói. Chưa chạy trên PostgreSQL/Windows của sinh viên.

| File | SHA256 |
|---|---|
| search.py trước (bàn giao 28/09) | `30c851204305b9aa5811c8a8260392001369cb39f510bdd87fc5eb18e4c7f9fc` |
| search.py sau | `1d82cbd76bdcc19c1f5d469b03e79d87ba021468c7e9b22b1f65d1b65bbedbb2` |
| danh_gia_tu_nhien.py (TN-20260928-1) | `d8e38a80fd8571cf327f80fbdb78c0dd5d4ff5d1f877e08bd178f83338cf33ee` |
| bo_de_tu_nhien.csv (chưa gán nhãn) | `fad16617b79d795de51c25c696cad6a7fe75195fbd7862be111af0b80c9aebcc` |

Báo cáo thô: `bao_cao_abc_sau_sua_mau_so.txt`, `bao_cao_tu_nhien_truoc.txt`, `bao_cao_tu_nhien_sau.txt`. Sau khi gán nhãn, SHA256 bộ đề sẽ đổi; khi đó chạy lại cả bản trước và sau với cùng file để so sánh.
