"""Công cụ whitelist cũ đã ngừng dùng vì không kiểm chứng được tính toàn vẹn XML.

Chạy file này chỉ hiện giải thích, không đăng nhập API hoặc thay đổi dữ liệu.
Muốn kiểm tra parser phải đối chiếu XML phản hồi thực với JSON của cùng thủ tục,
bao gồm thuộc tính XML, mixed content và trường lặp. Danh sách tên trường viết
cứng không đủ làm bằng chứng rằng parser giữ nguyên mọi dữ liệu.
"""

if __name__ == "__main__":
    print("Công cụ kiểm tra danh sách trường cũ đã ngừng sử dụng.")
    print("Chưa thể kết luận XML được bảo toàn chỉ từ tên trường.")
    print("Cần XML gốc và JSON của cùng thủ tục để đối chiếu; xem mục 7 của 02_TOM_TAT_TIEN_DO.md.")
