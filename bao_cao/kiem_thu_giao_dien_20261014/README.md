# Kiểm tra giao diện 14/10/2026

Cùng 70 phép kiểm tra trên Chromium 153.0.8010.0, FastAPI thật, Linux/Python 3.12.14, SQLite cô lập. Trước: 65/70; sau: 70/70. Không kiểm thử PostgreSQL thật hoặc LLM thật ở đợt này.

Kế thừa 59 phép ngày 13/10; kiểm tra phông chữ chấp nhận cả phông tự lưu và phông hệ thống hoạt động ngoại tuyến. Thêm 11 phép: vùng cuộn hội thoại, vị trí ô nhập, giảm chuyển động, trả lời dài trên điện thoại và 12 liên kết nhu cầu. Cùng một bộ chạy trước/sau. Trường Python trong JSON được ghi theo môi trường thực chạy, thay hằng 3.10 còn lại trong harness cũ; kết quả từng phép thử không bị sửa.

Dữ liệu chức năng: metadata 9.451 thủ tục, 21 mẫu chi tiết, cộng các bản ghi KT/NB có nhãn kiểm thử để kiểm tra XSS, số lượng giấy tờ, đăng nhập và bản nháp. Số thống kê nhật ký vì thế khác kho PostgreSQL của sinh viên. Các bản ghi kiểm thử không nằm trong mã sản phẩm hoặc ảnh sản phẩm đi kèm.

Đã đối chiếu JSON nguồn, đủ 240 dòng phí của thủ tục đất đai mẫu, dấu tích, ngữ cảnh hỏi tiếp, hủy phản hồi cũ, bàn phím và các trang ở 320/390/768/1440 px. Không có lỗi JavaScript trong các luồng được thử. Hai JSON chứa kết quả từng ca.

Kiểm tra thêm trên Windows: thử Enter/gợi ý; đọc thủ tục dài ở cả hai chế độ; tích ô rồi tải lại; hỏi hồ sơ rồi hỏi tiếp lệ phí; xóa hội thoại; đăng nhập cán bộ, lưu nháp và kiểm tra trang công dân. Thử cửa sổ hẹp hoặc chế độ điện thoại.
