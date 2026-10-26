# Báo cáo cải tiến tra cứu — 25/09/2026

> Báo cáo lịch sử thí nghiệm search. Bản starter kit 28/09/2026 đã sửa thêm cache, lọc, crawler và giao diện; dùng `../DOC_TRUOC_KHI_CHAY.md` để cập nhật cả gói. Mục 7 “chưa sửa” và hướng dẫn chép từng file ở mục 8 dưới đây mô tả thời điểm 25/09, không phải toàn bộ hiện trạng mới. Gói bằng chứng được đặt cùng thư mục với báo cáo này.

## 1. Kết luận

Giữ thay đổi tăng điểm 30% khi toàn bộ truy vấn từ hai âm tiết trở lên xuất hiện liên tiếp trong tiêu đề. Trên bộ đề nền 500 truy vấn mỗi nhóm, B Top-1 tăng từ 69,0% lên 72,0% (+3,0 điểm phần trăm, thêm 15 truy vấn đứng đầu); B Top-5 tăng từ 96,4% lên 97,2%. A Top-1 tăng từ 88,6% lên 90,8% và A Top-5 tăng từ 99,4% lên 99,8%. MRR của cả hai nhóm tăng, tỷ lệ không tìm thấy ID gốc vẫn bằng 0%.

Đây là kết quả thực nghiệm trên một kho và các bộ truy vấn được mô tả dưới đây; không phải cam kết chất lượng cho mọi câu hỏi người dân.

## 2. Dữ liệu và cách tái lập

- Nguồn: du_lieu_danh_gia.json do sinh viên xuất từ PostgreSQL, 9.451 thủ tục published.
- SHA256 kho: `2319b44b115bce195082764a04cdfa64ab6765bd6d559537b2583b951f8de685`.
- Bộ đo: danh_gia.py, ABC-20260924-1; mã nguồn bộ đo giữ nguyên trong toàn bộ thử nghiệm.
- SHA256 bộ đo: `a96e9ef5fbba8e34e630e37e464112cb2532742335ea57851d1fe9cace7b904f`.
- Chạy trực tiếp hàm main() của danh_gia.py. Tầng đọc DB được nối với các bản ghi JSON thật bằng adapter chỉ đọc trong experiments/run_evaluation.py; không dùng kho giả lập. Thuật toán search.py và cách sinh truy vấn/tính chỉ số không được thay thế bằng bản mô phỏng.
- Không có kết nối trực tiếp đến PostgreSQL hoặc server Windows của sinh viên trong môi trường đo này. Đây là phép đo thuật toán, không phải kiểm thử tích hợp API/giao diện.
- Báo cáo nền tái lập giống hoàn toàn nội dung bao_cao_nen_ABC_500.txt sinh viên gửi, sau khi thống nhất xuống dòng Windows/Linux. Cả SHA kho, SHA bộ đề A/B/C, các chỉ số và ví dụ đều khớp.
- Trong kho có 397 nhóm tên trùng sau chuẩn hóa, gồm 822 bản ghi; không có mã thủ tục không rỗng bị lặp. Trùng tên không chứng minh các thủ tục tương đương về nội dung hay hiệu lực, nên không gộp hoặc xóa.

## 3. Thay đổi và lý do

BM25 hiện tại cộng điểm các âm tiết và cặp âm tiết. Một tài liệu có thể đạt điểm cao khi những đơn vị đó nằm ở nhiều vị trí khác nhau, dù không chứa cả cụm truy vấn liên tiếp. Trong các trường hợp chưa đứng đầu của bộ nền, có 14 ca A và 20 ca B mà tiêu đề đứng đầu không chứa trọn cụm truy vấn.

Bản mới lưu thêm tiêu đề chuẩn hóa có dấu và không dấu trong chỉ mục. Sau khi tính BM25 và điều chỉnh dấu như cũ:

- Nếu truy vấn có ít nhất hai âm tiết và khớp trọn một đoạn liên tiếp trong tiêu đề, nhân điểm với `HE_SO_CUM_LIEN_TIEP = 1.3`.
- So khớp có ranh giới âm tiết, tránh khớp một phần bên trong âm tiết.
- Truy vấn có dấu so với bản tiêu đề có dấu; truy vấn không dấu so với bản không dấu.
- Không khớp trọn cụm vẫn được chấm theo thuật toán cũ; không có điều kiện bắt buộc phải khớp cụm để lọt vào tập ứng viên.

Hệ số 1,3 là tham số thực nghiệm của phần bổ sung, không phải tham số chuẩn BM25. Điểm sau điều chỉnh tiếp tục được quy đổi theo cơ chế phần trăm hiện có; phần trăm này là điểm tương đối, không phải xác suất kết quả đúng.

Các hàm thay đổi: xay_chi_muc() lưu thêm tiêu đề chuẩn hóa; cham_diem() bổ sung hệ số; chuan_bi_truy_van() sắp xếp đơn vị trước khi tính điểm; search() dùng ID tăng dần khi điểm bằng nhau. Không sửa giao diện hàm search(), các ngưỡng, cách tra tần suất, tập ứng viên, xếp hạng toàn kho trước lọc, parser, dữ liệu gốc hoặc nội dung toàn văn.

Trong kiểm tra tái lập đã phát hiện sai số cộng số thực và thứ tự duyệt tập hợp có thể đảo một số kết quả gần bằng điểm. Bản bàn giao cố định thứ tự đơn vị truy vấn và dùng ID để quyết định thứ tự khi điểm bằng nhau; ID không được xem là bằng chứng liên quan. Chạy lại danh_gia.py sau cả hai thay đổi vẫn giữ nguyên các chỉ số A/B đạt được ở mức 1,3. Hai tiến trình có PYTHONHASHSEED khác nhau đã cho cùng ID, điểm và phần trăm trên 105 lượt truy vấn thực (100 truy vấn lấy đều từ bộ đề và 5 ca từng quan sát dao động).

## 4. Các hệ số đã thử

| Hệ số | A Top-1 (%) | A Top-5 (%) | A MRR | B Top-1 (%) | B Top-5 (%) | B MRR |
|---|---:|---:|---:|---:|---:|---:|
| 1,00 (gốc) | 88.6 | 99.4 | 0.934218 | 69.0 | 96.4 | 0.805129 |
| 1,15 | 90.4 | 99.8 | 0.946650 | 71.8 | 97.0 | 0.825701 |
| 1,30 | 90.8 | 99.8 | 0.949750 | 72.0 | 97.2 | 0.826879 |
| 1,50 | 90.8 | 99.8 | 0.949750 | 72.0 | 97.2 | 0.826879 |

Chọn 1,3 vì đạt cùng các chỉ số A/B với 1,5 nhưng mức tăng điểm nhỏ hơn. Mọi cấu hình được chạy bằng danh_gia.py trên cùng kho và cùng bộ đề. Nhóm C chỉ tham khảo, không dùng để chọn hệ số.

## 5. Kết quả trước/sau của file bàn giao

| Nhóm | Chỉ số | Trước | Sau |
|---|---|---:|---:|
| A | Top-1 (%) | 88.6 | 90.8 |
| A | Top-5 (%) | 99.4 | 99.8 |
| A | MRR | 0.934218 | 0.949750 |
| A | Không thấy ID gốc (%) | 0.0 | 0.0 |
| A | Số kết quả trung bình | 10.34 | 4.73 |
| B | Top-1 (%) | 69.0 | 72.0 |
| B | Top-5 (%) | 96.4 | 97.2 |
| B | MRR | 0.805129 | 0.826879 |
| B | Không thấy ID gốc (%) | 0.0 | 0.0 |
| B | Số kết quả trung bình | 15.64 | 7.71 |
| C | Top-1 (%) | 19.6 | 21.6 |
| C | Top-5 (%) | 44.6 | 49.2 |
| C | MRR | 0.314620 | 0.342031 |
| C | Không thấy ID gốc (%) | 23.0 | 20.2 |
| C | Số kết quả trung bình | 43.25 | 32.72 |

Kiểm tra thứ hạng từng đáp án trong 500 truy vấn:

- A: 18 tăng hạng, 0 giảm hạng, 482 giữ nguyên.
- B: 35 tăng hạng, 1 giảm hạng, 464 giữ nguyên.

Trường hợp B giảm hạng là ID 4116 với truy vấn `duyet ke hoach lua`, từ hạng 1 xuống hạng 2 khi dùng quy tắc đồng điểm ổn định. Do đó chỉ kết luận các chỉ số tổng hợp cải thiện; không khẳng định từng truy vấn đều tốt hơn.

Số kết quả trung bình giảm không tự động đồng nghĩa độ chính xác tăng; phần này chịu ảnh hưởng ngưỡng tương đối 55% điểm đầu bảng đang có. Chỉ kết luận về vị trí ID đáp án theo các chỉ số đã đo.

## 6. Kiểm tra bổ sung sau khi chọn hệ số

Mỗi nhóm chọn thêm 500 ID thủ tục không thuộc bất kỳ bộ A/B/C 500 mẫu dùng để chọn hệ số. Kho dùng tính IDF vẫn là toàn bộ 9.451 thủ tục, chỉ tập ID dùng làm đáp án kiểm tra được tách. Seed bổ sung là 20260924 cho A và 20260925 cho B.

Các truy vấn có dấu được lấy từ chính tiêu đề của các ID bổ sung, chuẩn hóa bằng norm_dau() hiện tại rồi cắt theo quy tắc A/B. Giữ nguyên hệ số 1,3 sau khi xem kết quả bổ sung.

| Bộ bổ sung | Số mẫu | Top-1 trước → sau (%) | Top-5 trước → sau (%) | MRR trước → sau | Số đáp án tụt hạng |
|---|---:|---:|---:|---:|---:|
| A, không dấu | 500 | 89.0 → 91.2 | 99.8 → 100.0 | 0.937883 → 0.952667 | 0 |
| B, không dấu | 500 | 67.6 → 71.0 | 96.4 → 97.8 | 0.798695 → 0.823291 | 1 |
| A, có dấu | 500 | 89.8 → 91.6 | 99.4 → 100.0 | 0.940210 → 0.954667 | 0 |
| B, có dấu | 500 | 68.2 → 70.2 | 97.2 → 97.8 | 0.801697 → 0.820133 | 1 |

Lưu ý: tách theo ID, không tách theo nhóm tên trùng hoặc nhóm chủ đề; bộ bổ sung vẫn là truy vấn tự sinh từ tiêu đề, không phải tập câu hỏi tự nhiên có nhãn của người dùng. Các bảng này là kiểm tra bổ sung, không thay thế hoặc trộn vào mốc A/B chính.

Kiểm tra mã: file biên dịch thành công; giao diện hàm search() và các hàm _idf(), _gan_ket(), normalize() giữ nguyên; đã kiểm tra bằng bản ghi thật rằng khớp cụm chỉ trong lĩnh vực không nhận thưởng tiêu đề và 20 truy vấn có dấu khớp tiêu đề nhận đúng hệ số.

## 7. Giới hạn và việc chưa làm

- A chỉ dùng tối đa 25 âm tiết đầu; B là đoạn cắt liên tiếp nên đôi khi mất thông tin phân biệt hoặc cắt giữa một từ nhiều âm tiết.
- Bộ đo chấm theo một ID gốc. Tên trùng hoặc truy vấn mơ hồ vẫn có thể đưa một thủ tục hợp lý khác lên trước.
- Chưa chứng minh cải thiện truy vấn đồng nghĩa, lỗi gõ, câu hỏi dài tự nhiên hoặc thông tin không có trong tên/lĩnh vực.
- Không đánh giá tính đầy đủ của XML, phí, thời hạn, điều kiện hoặc hiệu lực: JSON xuất không có nội dung data.
- Bản cũ có thể dao động nhẹ ở các thứ hạng gần bằng điểm giữa tiến trình; bảng nền là lần chạy tái lập khớp báo cáo sinh viên. Bản mới đã thêm thứ tự tính điểm và quy tắc đồng điểm để giảm vấn đề này.
- Không sửa các rủi ro đã báo như làm mới cache theo số lượng, giới hạn kết quả trước lọc, Unicode/stopwords hoặc hiển thị phí.
- Chưa đo hiệu năng trên máy Windows; thời gian chạy tại môi trường thử nghiệm không được dùng làm số liệu tốc độ cho báo cáo.

## 8. Cài bản mới trên Windows

1. Trong cửa sổ server đang chạy, nhấn Ctrl+C.
2. Mở CMD, chạy:

```bat
cd /d C:\Users\Admin\Downloads\starter_kit\starter\backend
venv\Scripts\activate
copy app\search.py app\search_truoc_cai_tien.py
```

3. Chép file search.py được bàn giao đè vào backend\app\search.py. Giữ nguyên danh_gia.py ABC-20260924-1 và kho dữ liệu trong lần đối chiếu.
4. Chạy lại bộ đo trên PostgreSQL thật của máy:

```bat
python danh_gia.py 500 --luu bao_cao_sau_cai_tien_ABC_500.txt
```

5. Chạy lại server:

```bat
uvicorn app.main:app
```

Nếu SHA kho hoặc SHA bộ đề thay đổi, chưa so trực tiếp chỉ số mới với bảng này. Nếu SHA kho/bộ đề giữ nguyên nhưng số đo khác, gửi báo cáo để kiểm tra môi trường và việc chép file.

Hoàn tác khi cần: tắt server bằng Ctrl+C, tại backend và sau khi kích hoạt venv chạy:

```bat
copy /Y app\search_truoc_cai_tien.py app\search.py
uvicorn app.main:app
```

## 9. Tái lập độc lập từ gói bằng chứng

Gói ZIP chứa dữ liệu JSON đã xuất, mã nguồn trước/sau, bộ đo không đổi, adapter chỉ đọc và báo cáo của các lần chạy. Báo cáo chính nằm ở experiments/reports/baseline.txt và experiments/reports/final.txt; các file báo cáo khác là cấu hình trung gian. Không chứa .env, mật khẩu hoặc token. Adapter này chỉ dùng đo offline, không thay thế backend triển khai.

Sau khi giải nén, tại thư mục gốc của gói chạy bằng Python 3.10+ (chỉ dùng thư viện chuẩn; có thể dùng Python trong venv đang có):

```bat
python experiments/run_evaluation.py --search upload/search.py --report experiments/reports/baseline_tai_lap.txt --trace experiments/baseline_trace.json
python experiments/run_evaluation.py --search deliverables/search.py --report experiments/reports/final_tai_lap.txt --trace experiments/final_trace.json
python experiments/validate_candidate.py
```

Báo cáo chính tái lập luôn dùng danh_gia.py. Script validate_candidate.py chỉ là kiểm tra bổ sung, tách rõ bộ đề và giữ nguyên dữ liệu thật. Các lần chạy trên Windows với PostgreSQL bằng lệnh ở mục 8 vẫn là bước xác nhận môi trường triển khai.

## 10. Dấu kiểm tra mã nguồn bàn giao

- search.py trước: `1669d8642e3f39324b8d9448b95aa7703b1c578502a0d63760a5b51e071f59ce`.
- search.py sau: `30c851204305b9aa5811c8a8260392001369cb39f510bdd87fc5eb18e4c7f9fc`.
