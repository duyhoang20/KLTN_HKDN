# Hướng dẫn đưa mã nguồn lên GitHub an toàn

Mục tiêu: đưa toàn bộ thư mục này lên GitHub **mà không lộ bất kỳ mật khẩu hay tài khoản nào**. Làm theo thứ tự, mỗi bước chỉ mất vài phút.

## 1. Quyết định chế độ của kho mã

- **Private (khuyến nghị):** chỉ bạn và người được mời mới xem được. Muốn cho thầy cô xem thì vào *Settings → Collaborators → Add people* và mời tài khoản GitHub của thầy cô.
- **Public:** ai cũng xem được. Chỉ chọn khi **anh hướng dẫn ở VNPT Gia Lai đã đồng ý**, vì kho có dữ liệu thủ tục lấy bằng quyền truy cập do đơn vị cấp (`du_lieu_mau/`, `bao_cao/`).

## 2. Kiểm tra trước khi đưa lên

Mở thư mục gốc của kho (nơi có `README.md`) và chắc chắn:

1. **Không có tệp `.env` thật** đi kèm. Nếu bạn chép thư mục này đè lên thư mục đang chạy trên máy, tệp `backend/.env` của bạn sẽ nằm trong đó. Tệp `.gitignore` đã chặn nó, nhưng vẫn nên kiểm ở bước 4.
2. Không có `backend/venv/`, `backend/du_lieu_demo.db`, `azure_deploy.zip`. Các tệp này cũng đã bị `.gitignore` chặn.

## 3. Tạo kho trên GitHub

1. Đăng nhập https://github.com, bấm **New repository**.
2. Đặt tên, ví dụ `tra-cuu-thu-tuc-hanh-chinh`; chọn **Private**.
3. **Không** tích *Add a README*, *.gitignore* hay *license*, vì kho này đã có sẵn các tệp đó.
4. Bấm **Create repository**, rồi chép địa chỉ dạng `https://github.com/<tên-bạn>/tra-cuu-thu-tuc-hanh-chinh.git`.

## 4. Đưa mã lên (cài Git từ https://git-scm.com nếu máy chưa có)

Mở CMD tại thư mục gốc của kho:

```bat
git init
git add .
git status
```

**Đọc kỹ danh sách `git status` in ra.** Nếu thấy dòng nào chứa `.env` (trừ `backend/.env.example`), `venv` hoặc `.db`, thì **dừng lại**, chạy `git rm --cached <tên tệp>` và kiểm tra lại `.gitignore`. Một lệnh kiểm tra nhanh:

```bat
git ls-files | findstr /i "\.env venv \.db"
```

Kết quả chỉ được có một dòng `backend/.env.example`. Khi đã chắc chắn:

```bat
git commit -m "Khóa luận: hệ thống tra cứu thủ tục hành chính và trợ lý AI"
git branch -M main
git remote add origin https://github.com/<tên-bạn>/tra-cuu-thu-tuc-hanh-chinh.git
git push -u origin main
```

Lần đầu `git push`, Git sẽ mở cửa sổ đăng nhập GitHub trên trình duyệt.

## 5. Nếu lỡ đưa mật khẩu lên

Xóa tệp khỏi GitHub **không đủ**, vì lịch sử commit vẫn còn. Cần làm ngay:

1. **Đổi mọi mật khẩu đã lộ:** mật khẩu database (Azure → PostgreSQL flexible server → *Reset password*), mật khẩu cán bộ, `BI_MAT_PHIEN`, và báo đơn vị cấp tài khoản API nếu tài khoản đó bị lộ.
2. Cập nhật mật khẩu mới trong *App Service → Environment variables* và trong `backend/.env` trên máy.
3. Nếu kho đang Public, chuyển sang Private trong lúc xử lý.

## 6. Cập nhật về sau

```bat
git add .
git status
git commit -m "Mô tả ngắn thay đổi"
git push
```

Luôn đọc `git status` trước khi `commit`.
