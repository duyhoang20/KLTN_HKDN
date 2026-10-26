# HƯỚNG DẪN GÁN NHÃN BỘ ĐỀ CÂU HỎI TỰ NHIÊN

## Vì sao cần bộ đề này

Bộ đo `danh_gia.py` (A/B/C) sinh truy vấn bằng cách cắt từ chính tên thủ tục, nên nó không bao giờ chứa từ đệm ("cần những gì", "như thế nào"), từ đồng nghĩa ("sổ đỏ", "bằng lái") hay cách nói đời thường. Kiểm tra ngày 28/09 cho thấy chính những truy vấn đó là chỗ hệ thống yếu nhất, mà bộ A/B/C không nhìn thấy. Bộ đề này lấp chỗ trống đó, và cũng sẽ là thước đo cho trợ lý AI sau này.

## Các file

| File | Vai trò |
|---|---|
| `bo_de_tu_nhien.csv` | 50 câu hỏi; bạn điền cột `ma_thu_tuc_dung`. Mở được bằng Excel |
| `ung_vien_goi_y.txt` | Với mỗi câu, danh sách thủ tục có tên chứa khái niệm liên quan, kèm mã |
| `../backend/danh_gia_tu_nhien.py` | Bộ đo đọc file CSV và tính chỉ số |

Các câu chia bốn loại (cột `loai`): `tu_nhien` — câu hỏi đời thường (37 câu); `dong_nghia` — dùng từ đồng nghĩa hoặc thuật ngữ cũ (9 câu); `khong_dau` — gõ không dấu (4 câu); `ngoai_pham_vi` — câu không liên quan thủ tục hành chính (15 câu, STT 51–65, **nhãn `KHONG_CO` đã điền sẵn**, không cần gán).

Câu ngoài phạm vi dùng để đo chiều ngược lại: hệ thống phải **trả rỗng**. Bản sửa ngày 28/09 từng làm 50 câu trong phạm vi hết trả rỗng, nhưng đồng thời trả kết quả sai tới 100% cho câu như "cách nấu phở bò"; bộ đề khi đó chỉ có câu trong phạm vi nên không phát hiện được. Từ nay mọi thay đổi phải qua cả hai chiều.

**Đã gán nhãn bản 50 câu trước đây?** Giữ file của bạn, chép thêm dòng 51–65 từ file mới vào cuối.

## Cách gán nhãn

Với mỗi câu, tự hỏi: **"Nếu người dân gõ câu này, thủ tục nào là thứ họ thực sự cần?"** Điền **mã thủ tục** (dạng `1.001471`, không phải ID) vào cột `ma_thu_tuc_dung`.

**Nhiều đáp án đúng** thì ghi hết, cách nhau bằng dấu chấm phẩy: `1.001471; 1.001456`. Thường gặp khi cùng một thủ tục có bản cấp tỉnh và cấp trung ương, hoặc bản có chíp và không chíp. Hệ thống được tính đúng nếu trả về bất kỳ mã nào trong danh sách.

**Câu mơ hồ** thì chọn theo cách hiểu phổ biến nhất của người dân, ghi lý do ở cột `ghi_chu`. Ví dụ "làm hộ chiếu cần những gì": người dân thường làm hộ chiếu phổ thông, không phải hộ chiếu ngoại giao.

**Kho không có thủ tục phù hợp** thì ghi `KHONG_CO`. Với câu này, kết quả mong muốn là hệ thống trả về rỗng.

**Chưa chắc** thì để trống; bộ đo tự bỏ qua câu chưa gán nhãn.

## Gán nhãn bằng Excel cho an toàn

Excel hay làm hỏng mã thủ tục mà không báo: `2.000720` thành `2.00072` (bỏ số 0 cuối), hoặc với thiết lập vùng Việt Nam, `1.001471` bị hiểu dấu chấm là phân cách hàng nghìn thành `1001471`. Làm theo thứ tự:

1. Mở Excel trống, chọn Data > From Text/CSV, chọn `bo_de_tu_nhien.csv`, bảng mã **65001: Unicode (UTF-8)**.
2. Trước khi nạp, chọn Transform Data (hoặc bước chọn kiểu cột), đặt cột `ma_thu_tuc_dung` là **Text**.
3. Gán nhãn xong, File > Save As > **CSV UTF-8 (Comma delimited) (\*.csv)**, ghi đè file cũ.

Cách đơn giản hơn: mở file bằng Notepad và gõ mã trực tiếp, mỗi dòng dạng `1,làm hộ chiếu cần những gì,tu_nhien,1.001471; 1.001456,`.

Nếu lỡ lưu sai, bộ đo sẽ dừng và báo từng dòng lỗi, kèm gợi ý mã đúng khi đoán được — không có chuyện âm thầm tính sai.

## Dùng file ứng viên như thế nào

`ung_vien_goi_y.txt` liệt kê các thủ tục có tên chứa một khái niệm mình đặt sẵn cho từng câu (ví dụ câu "xin cấp sổ đỏ lần đầu" lọc theo "giấy chứng nhận quyền sử dụng đất"). Danh sách này được lọc bằng **khớp chữ thuần túy**, cố ý **không** dùng thuật toán tra cứu của hệ thống — nếu dùng, bộ đề sẽ thiên vị đúng thuật toán nó đang chấm.

Hai lưu ý: đáp án đúng **có thể không nằm** trong danh sách ứng viên, khi đó tìm trên giao diện hoặc pgAdmin rồi điền mã; và **đừng chọn đáp án theo kết quả hệ thống đang trả về** — điền theo điều người dân cần.

## Chạy bộ đo

Trong thư mục `backend`, sau khi kích hoạt venv:

```bat
python danh_gia_tu_nhien.py --luu bao_cao_tu_nhien.txt
```

Bộ đo kiểm tra toàn bộ file trước khi tính. Có lỗi (mã sai, `KHONG_CO` đi cùng mã, STT hoặc câu trùng, file không phải UTF-8…) thì dừng với mã thoát 2 và liệt kê từng dòng lỗi. Sửa hết rồi chạy lại.

Chưa gán câu nào thì bộ đo vẫn chạy: báo tỉ lệ trả về rỗng và chỉ số của 15 câu ngoài phạm vi. Nên gán đủ 50 câu trước khi đưa số liệu vào báo cáo.

Các chỉ số. **Trong phạm vi**: Top-1, Top-5, MRR, trả về rỗng, lạc đề (có kết quả nhưng không có đáp án đúng). **Ngoài phạm vi**: tỉ lệ từ chối đúng, và phần trăm cao nhất hiển thị trên câu trả lời sai. Báo cáo tách theo loại câu và in 3 kết quả đầu của mỗi câu, đánh dấu ✓ ở đáp án đúng.

## Nguyên tắc khi dùng bộ đề để cải tiến

Sau khi gán nhãn xong, **không sửa đáp án** để hợp với kết quả hệ thống. Nếu thấy mình gán nhầm thì sửa, ghi vào `ghi_chu`, và đo lại cả bản trước lẫn bản sau với cùng file (dòng "SHA256 bộ đề" phải giống nhau thì mới so sánh được).

Bộ đề chỉ có 50 câu nên mỗi câu chiếm 2 điểm phần trăm; chênh lệch 1–2 câu chưa đủ để kết luận. Khi tinh chỉnh, xem song song cả bộ này và bộ A/B/C: một thay đổi chỉ nên giữ nếu không làm giảm A/B.

Không được dùng chính 50 câu này để vừa chọn tham số vừa báo cáo kết quả cuối. Nếu dùng chúng để tinh chỉnh, hãy soạn thêm một bộ câu khác (không nhìn trước kết quả) để kiểm tra lần cuối.
