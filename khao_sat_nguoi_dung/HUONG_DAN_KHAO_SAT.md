# Khảo sát với người dùng thật — hướng dẫn thực hiện (bổ sung 21/10/2026)

Mục đích: có bằng chứng **người thật** dùng được hệ thống, và có một bộ câu hỏi do người khác nghĩ ra (độc lập với người viết từ điển đồng nghĩa). Mất khoảng 20 phút cho mỗi người, nên làm với 5–8 người.

**Không bịa kết quả.** Chỉ ghi những gì thực sự quan sát được. Nếu chỉ làm được 3 người thì báo cáo 3 người. Tệp `ket_qua_khao_sat_MAU.csv` có một dòng **ví dụ** (mã `VI_DU_01`); xóa dòng đó trước khi nhập dữ liệu thật.

## 1. Chuẩn bị

- Chạy hệ thống trên máy của bạn (hoặc dùng link Render). Mở sẵn trang chủ ở một cửa sổ mới.
- In hoặc mở sẵn phiếu SUS ở mục 4.
- Mỗi người thử có một mã (NT01, NT02…). **Không ghi họ tên, số điện thoại** vào tệp kết quả.
- Đọc cho người thử nghe lời mời ở mục 2 và chỉ bắt đầu khi họ đồng ý.

Nên chọn người thử đa dạng: sinh viên; người đi làm; người lớn tuổi hoặc ít dùng máy tính; nếu được, một cán bộ ở VNPT.

## 2. Lời mời (đọc cho người thử)

> “Mình đang thử một trang tra cứu thủ tục hành chính làm cho đồ án tốt nghiệp. Mình nhờ anh/chị làm 4 việc nhỏ trên trang, rồi trả lời 10 câu hỏi ngắn. Mình đang thử TRANG WEB, không phải thử anh/chị, nên không có câu trả lời sai. Anh/chị cứ vừa làm vừa nói ra mình đang nghĩ gì. Mình chỉ ghi lại việc anh/chị làm và thời gian, không ghi tên. Anh/chị có thể dừng bất cứ lúc nào. Anh/chị đồng ý chứ?”

## 3. Bốn nhiệm vụ (đọc từng việc; không gợi ý cách làm)

| Mã | Nhiệm vụ | Được tính là hoàn thành khi |
|---|---|---|
| NV1 | “Con anh/chị 10 tuổi cần làm hộ chiếu lần đầu. Hãy tìm xem cần chuẩn bị những giấy tờ gì.” | Mở đúng thủ tục cấp hộ chiếu phổ thông và đọc được danh sách giấy tờ |
| NV2 | “Hãy tìm lệ phí đăng ký khai sinh, và nộp hồ sơ ở đâu.” | Nói đúng thông tin lệ phí (hoặc “nguồn không ghi”) và nơi nộp theo trang |
| NV3 | “Anh/chị muốn biết làm thủ tục giám hộ cho cháu mình thì nộp ở đâu.” | Mở đúng thủ tục đăng ký giám hộ |
| NV4 | “Hãy tự hỏi trợ lý MỘT câu về một thủ tục anh/chị từng làm hoặc sắp làm.” | Ghi nguyên văn câu hỏi, và người thử tự đánh giá câu trả lời có dùng được không (có/không) |

Với mỗi nhiệm vụ, ghi vào CSV:
- `hoan_thanh`: `co` hoặc `khong`;
- `thoi_gian_giay`: tính từ lúc đọc xong nhiệm vụ đến lúc người thử nói “xong” hoặc bỏ cuộc;
- `so_lan_tim`: số lần bấm tìm hoặc gửi câu hỏi;
- `ghi_chu`: chỗ lúng túng, câu người thử đã gõ (nguyên văn), và lời nhận xét của họ.

Với NV4, chép nguyên văn câu hỏi của người thử vào `ghi_chu`. Các câu này về sau có thể thành một **bộ câu hỏi mới** (gán nhãn, rồi đo như các bộ khác). **Không** dùng chúng để chỉnh từ điển trước khi đo.

## 4. Phiếu SUS (System Usability Scale), sau khi làm xong 4 nhiệm vụ

Thang điểm: 1 = Hoàn toàn không đồng ý … 5 = Hoàn toàn đồng ý. Ghi vào cột `sus1`…`sus10` ở **một** dòng của người thử đó.

1. Tôi nghĩ tôi sẽ muốn dùng trang này thường xuyên.
2. Tôi thấy trang này phức tạp một cách không cần thiết.
3. Tôi thấy trang này dễ dùng.
4. Tôi nghĩ tôi cần người hướng dẫn kỹ thuật mới dùng được trang này.
5. Tôi thấy các chức năng của trang được kết hợp tốt với nhau.
6. Tôi thấy trang này có quá nhiều chỗ không nhất quán.
7. Tôi nghĩ hầu hết mọi người sẽ học cách dùng trang này rất nhanh.
8. Tôi thấy trang này rất rườm rà, khó dùng.
9. Tôi cảm thấy rất tự tin khi dùng trang này.
10. Tôi phải học nhiều thứ trước khi dùng được trang này.

Thêm hai câu hỏi mở (ghi vào `ghi_chu` của dòng NV4):
- “Điều gì làm anh/chị thấy khó chịu nhất?”
- “Anh/chị có tin câu trả lời của trợ lý không? Vì sao?”

## 5. Tính kết quả

```bat
cd /d "%DU_AN%\khao_sat_nguoi_dung"
python tinh_ket_qua.py ket_qua_khao_sat.csv
```

Kết quả gồm: tỉ lệ hoàn thành từng nhiệm vụ, thời gian trung vị, số lần tìm trung vị, điểm SUS của từng người và trung bình, cùng toàn bộ ghi chú. Mốc tham khảo thường dùng: điểm SUS khoảng 68 là mức trung bình.

## 6. Đưa vào báo cáo

- Một bảng: nhiệm vụ, số người hoàn thành trên tổng số, thời gian trung vị.
- Điểm SUS trung bình kèm số người (ví dụ “SUS 74,5; n = 6”). Với n nhỏ thì nói rõ đây là khảo sát định tính, không suy rộng.
- Ba chỗ người dùng lúng túng nhiều nhất, và bạn đã sửa hay chưa sửa (kèm lý do).
- Nhóm người thử (sinh viên, người đi làm…), ngày làm, máy và trình duyệt đã dùng.
