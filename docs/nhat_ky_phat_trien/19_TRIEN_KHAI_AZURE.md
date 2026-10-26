# Đưa trang web lên Azure for Students (chạy 24/24, không cần thẻ)

Hướng dẫn được cập nhật theo lần chạy thật trên Azure (các chỗ ghi “Đã gặp khi chạy thật”; kết quả ở mục 13). Làm trên máy Windows, khoảng 1–2 giờ cho lần đầu.

Kết quả cuối cùng là một địa chỉ dạng `https://<tên-app>.azurewebsites.net` mà ai cũng mở được, chạy liên tục, không ngủ. Có thể kèm một đoạn chữ ngẫu nhiên tùy vùng. Bạn **không cần mua tên miền**.

> **Trước khi bắt đầu:** dữ liệu lấy từ API iGate do đơn vị cấp quyền. Hãy hỏi người hướng dẫn ở VNPT xem có được đưa lên Internet công khai không.

## 0. Chi phí và giới hạn

| Dịch vụ | Gói | Tiền |
|---|---|---|
| Azure Database for PostgreSQL (flexible server) | Burstable **B1ms**, lưu trữ **32 GB** | **Miễn phí 12 tháng** (750 giờ/tháng, đủ chạy liên tục) |
| App Service (chạy web) | **Basic B1** (Linux) | Khoảng 13–15 USD/tháng, **trừ vào 100 USD credit** |

- Credit 100 USD đủ cho khoảng 6–7 tháng. Hết credit, Azure gửi email hỏi có chuyển sang trả tiền không. Nếu không chuyển, dịch vụ bị tắt, **không tự trừ tiền**.
- Không chọn gói **Free F1** cho App Service: gói này chỉ chạy 1 giờ CPU mỗi ngày, không chạy được 24/24.
- Chỉ được miễn phí database nếu chọn đúng **B1ms + 32 GB**, tắt High availability và tắt Geo-redundant backup.

Giao diện Azure thay đổi theo thời gian, nên tên nút có thể hơi khác. Bên dưới ghi kèm tên tiếng Anh để bạn dễ tìm.

## 1. Kích hoạt Azure for Students

1. Mở https://azure.microsoft.com/free/students, bấm **Start free**.
2. Đăng nhập hoặc tạo tài khoản Microsoft bằng **email trường UEH**, rồi làm theo bước xác minh sinh viên.
3. Vào https://portal.azure.com, tìm **Subscriptions** và thấy dòng **Azure for Students** là được.

Nếu email trường không được chấp nhận thì dừng ở đây và dùng Render (tài liệu 15).

## 2. Xem các vùng (region) được phép tạo dịch vụ

Tài khoản sinh viên chỉ được tạo dịch vụ ở một vài vùng, và danh sách này khác nhau giữa các tài khoản. Chọn sai vùng sẽ báo lỗi `RequestDisallowedByPolicy`.

1. Trên portal, tìm **Policy**, vào **Authoring → Assignments**.
2. Mở **Allowed resource deployment regions** và xem **Allowed locations**.
3. Chọn **một** vùng gần Việt Nam nhất có trong danh sách (ưu tiên Southeast Asia, East Asia, Japan, Korea, Australia). Dùng **cùng một vùng** cho cả database và web.

## 3. Tạo nhóm tài nguyên

Tìm **Resource groups**, bấm **Create**:
- Name: `rg-tracuu`
- Region: vùng đã chọn ở bước 2

## 4. Tạo database PostgreSQL

Tìm **Azure Database for PostgreSQL flexible servers** rồi bấm **Create**. Nếu được hỏi kiểu, chọn Flexible server.

**Tab Basics:**
- Resource group: `rg-tracuu`
- Server name: ví dụ `tracuu-db-<tên bạn>`, viết thường, không dấu
- Region: vùng ở bước 2
- PostgreSQL version: **18** (cùng bản chính với PostgreSQL 18 trên máy bạn; đã chạy thật với 18.6). Bản 16 cũng dùng được.
- Workload type: **Development**
- Bấm **Configure server**: Compute tier **Burstable**, size **Standard_B1ms**, Storage **32 GiB**, Storage autogrow **tắt**
- High availability: **Disabled**
- Authentication: **PostgreSQL authentication only**
- Admin username: ví dụ `tracuuadmin`. Không dùng `postgres` hay `admin`, Azure không cho.
- Password: **chỉ dùng chữ hoa, chữ thường và chữ số**, ít nhất 12 ký tự, ví dụ dạng `TracuuDb2026Xyz`. Không dùng ký tự đặc biệt để khỏi phải mã hóa trong chuỗi kết nối. **Ghi lại mật khẩu, không gửi cho ai.**

**Tab Networking:**
- Connectivity method: **Public access (allowed IP addresses)**
- Đánh dấu **Allow public access from any Azure service within Azure to this server**, để web trên Azure kết nối được
- Bấm **+ Add current client IP address**, để máy bạn chép dữ liệu lên được

**Tab Backup** (nếu có): Geo-redundancy **tắt**.

Bấm **Review + create**, rồi **Create**, chờ 5–10 phút.

**Tạo database `guidance_db`:** mở server vừa tạo, vào **Settings → Databases → + Add**, đặt tên `guidance_db`, rồi **Save**.

**Chuỗi kết nối** (thay 3 chỗ trong `< >`):

```
postgresql://<admin-username>:<mật-khẩu>@<server-name>.postgres.database.azure.com:5432/guidance_db?sslmode=require
```

`?sslmode=require` là bắt buộc vì Azure chỉ nhận kết nối mã hóa. Chuỗi này chứa mật khẩu: không dán vào báo cáo, không gửi qua chat, không đưa lên GitHub.

## 5. Chép dữ liệu từ máy bạn lên Azure

Không phải crawl lại. Mở CMD:

Thay `C:\duong-dan\toi\thu-muc-du-an` bằng thư mục dự án đang chạy trên máy (nơi có `backend\.env` và `backend\venv`).

```bat
set "DU_AN=C:\duong-dan\toi\thu-muc-du-an"
cd /d "%DU_AN%\backend"
venv\Scripts\activate
set PYTHONUTF8=1
set /p "DICH=Dan chuoi ket noi Azure roi Enter: "
python chuyen_du_lieu.py --den "%DICH%"
set "DICH="
```

Nếu `venv\Scripts\activate` báo lỗi (thường do thư mục `venv` được chép từ thư mục khác), bỏ dòng đó và gọi thẳng `venv\Scripts\python chuyen_du_lieu.py --den "%DICH%"`.

Khi CMD hỏi chuỗi kết nối, **dán chuỗi rồi mới bấm Enter**. Chạy lệnh `python ...` và lệnh `set "DICH="` ở **hai dòng riêng**; dán dính vào một dòng sẽ báo `unrecognized arguments`.

- Kết quả đúng: dòng cuối là `KẾT QUẢ: CHÉP ĐỦ VÀ KHỚP`.
- **Đã gặp khi chạy thật:**
  - `connection to server at "localhost" ... Connection refused`: PostgreSQL trên máy bạn đang tắt. Mở **Services**, chuột phải `postgresql-x64-18` → **Start** (nên đặt Startup type: Automatic).
  - `could not translate host name ... No such host is known`: bộ nhớ DNS của Windows giữ kết quả cũ. Chạy `ipconfig /flushdns` rồi chạy lại.
  - `Connection timed out` tới máy chủ Azure: kiểm cổng bằng PowerShell `Test-NetConnection <server-name>.postgres.database.azure.com -Port 5432`. Nếu `False`, thêm IP hiện tại ở Networking (dòng dưới); nếu vẫn `False`, mạng đang chặn cổng 5432, dùng 4G từ điện thoại.
- **Sau khi chép xong, đổi mật khẩu database** (server → Overview → **Reset password**), nhất là nếu chuỗi kết nối từng hiện trên màn hình hay bị gửi đi đâu. Mật khẩu mới dùng cho `DATABASE_URL` ở bước 7a.
- Báo lỗi hết thời gian chờ (timeout) hoặc "no pg_hba.conf entry": IP máy bạn đã đổi, chẳng hạn do đổi wifi. Vào server, mở **Settings → Networking**, bấm **+ Add current client IP address**, **Save**, rồi chạy lại.
- Công cụ chỉ đọc ở máy bạn. Database trên máy bạn vẫn là bản gốc.

## 6. Tạo Web App

Tìm **App Services**, chọn **Create → Web App**.

**Tab Basics:**
- Resource group: `rg-tracuu`
- Name: ví dụ `tracuu-thutuc-<tên bạn>`. Tên này nằm trong địa chỉ web. Đừng dùng chữ khiến người ta tưởng là trang của nhà nước (dichvucong, gov, chinhphu).
- Publish: **Code**
- Runtime stack: **Python 3.12**
- Operating System: **Linux**
- Region: vùng ở bước 2
- Pricing plan: **Create new**, chọn **Basic B1**. Không chọn Free F1.

**Tab Deployment:** không bật GitHub. **Tab Monitoring:** Application Insights chọn **No**, cho đỡ tốn credit.

Bấm **Review + create**, rồi **Create**.

## 7. Cấu hình Web App

Mở Web App vừa tạo.

**7a. Biến môi trường:** vào **Settings → Environment variables → App settings**, thêm từng dòng rồi bấm **Apply**:

| Name | Value |
|---|---|
| `DATABASE_URL` | chuỗi kết nối ở bước 4 |
| `QUAN_TRI_TAI_KHOAN` | tên đăng nhập cán bộ bạn tự đặt |
| `QUAN_TRI_MAT_KHAU` | mật khẩu cán bộ, đặt mới, dài, **khác** mật khẩu database |
| `BI_MAT_PHIEN` | chuỗi ngẫu nhiên, tạo bằng lệnh bên dưới |
| `GIOI_HAN_MOI_PHUT` | `60` (mỗi IP, mỗi nhóm API; 30 cũng được, nhưng nếu cả phòng demo dùng chung một mạng thì nên để 60–100) |
| `SO_PROXY_TIN_CAY` | `1` (tạm thời; kiểm lại ở bước 9) |
| `NHAT_KY_GIU_NGAY` | `180` |
| `PYTHONUTF8` | `1` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (để Azure tự cài thư viện) |

Tạo `BI_MAT_PHIEN` trên máy bạn:

```bat
python -c "import secrets; print(secrets.token_hex(32))"
```

**7b. Lệnh khởi động và chế độ chạy liên tục:** vào **Settings → Configuration**.
- Tab **General settings**: **Always on** = **On** (giữ cho trang không ngủ), **HTTPS only** = **On**, Minimum TLS 1.2, Client certificate mode = **Ignore**. Bấm **Apply → Continue**.
- Tab **Stack settings** (giao diện portal mới đặt ô này ở đây, không còn ở General settings): Stack **Python**, Version **Python 3.12**, ô **Startup command**:
  `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
  Bấm **Apply → Continue**. Nút Apply chuyển sang màu xám là đã lưu.

**7c. Kiểm tra sức khỏe: để sau.** Chưa bật lúc này, vì app chưa có mã nên chắc chắn “không khỏe” và Azure sẽ thay máy liên tục. Bật ở cuối bước 9.

## 8. Đóng gói và đưa mã lên

**8a. Đóng gói trên máy bạn:**

```bat
cd /d "%DU_AN%"
python dong_goi_azure.py
```

Script tạo `azure_deploy.zip`, chỉ gồm `backend/app`, `frontend` và tệp thư viện. Script tự kiểm và **dừng nếu thấy `.env`** trong gói. Không bao giờ nén tay cả thư mục `backend`, vì như vậy sẽ kéo theo `.env` và `venv`.

**8b. Đưa lên bằng Cloud Shell** (không cần cài gì thêm):

1. Trên portal, bấm biểu tượng **Cloud Shell** `>_` ở thanh trên cùng, chọn **Bash**. Nếu được hỏi lưu trữ, chọn **No storage account required**.
2. Bấm **Manage files → Upload**, chọn **đúng** `azure_deploy.zip` (khoảng 300 KB, ở thư mục gốc của dự án). **Đã gặp khi chạy thật:** lỡ chọn tệp nén cả thư mục dự án (có `.env`) → xóa ngay trong Cloud Shell bằng `rm -f "<tên tệp>"`. Kiểm bằng `ls -la azure_deploy.zip`.
3. Chạy lệnh (thay `<tên-app>`):

```bash
az webapp deploy --resource-group rg-tracuu --name <tên-app> --src-path azure_deploy.zip --type zip
```

Chờ 3–7 phút để Azure cài thư viện và khởi động.

**Đã gặp khi chạy thật:** lần đầu, lệnh báo `Deployment failed because the site failed to start within 10 mins` dù nhật ký build `Errors (0)`. Container dừng lâu ở bước `Updating certificates` của nền tảng trước khi chạy Startup Command; Azure tự khởi động lại và trang lên bình thường. Vì vậy **đừng deploy lại ngay**: chờ thêm 5 phút rồi kiểm
`curl -s -m 120 -w "\nHTTP %{http_code}\n" https://<địa-chỉ-app>/health`
Ra `HTTP 200` là xong. Nếu vẫn lỗi, xem nhật ký:
```bash
az webapp log config -n <tên-app> -g rg-tracuu --docker-container-logging filesystem
az webapp restart -n <tên-app> -g rg-tracuu
az webapp log download -n <tên-app> -g rg-tracuu --log-file logs.zip && unzip -o -q logs.zip -d logs
tail -n 40 $(ls -t logs/LogFiles/*_default_docker.log | head -1)
```
Mỗi lần khởi động lại có thể mất vài phút; hạn chế Restart và đổi cấu hình trong những ngày chấm bài.

*Cách khác:* cài Azure CLI trên Windows bằng `winget install -e --id Microsoft.AzureCLI`, mở CMD mới, chạy `az login`, rồi chạy cùng lệnh trên trong thư mục có `azure_deploy.zip`.

## 9. Kiểm tra sau khi chạy

1. Mở `https://<địa-chỉ-app>/san-sang`. Đúng là `{"san_sang":true,"so_thu_tuc_cong_khai":...}`, với số khoảng 9.460.
2. Mở trang chủ `/`, thử tra "làm sổ đỏ", thử hỏi trợ lý.
3. Mở `/quan_tri.html`, đăng nhập bằng tài khoản cán bộ ở bước 7a.
4. **Bắt buộc:** kiểm số lớp proxy. Trang chẩn đoán cần mã phiên gửi trong tiêu đề `Authorization`, nên **mở thẳng địa chỉ ở thẻ mới sẽ báo “Cần đăng nhập”**. Cách đúng: ở thẻ `/quan_tri.html` **đang đăng nhập**, mở Console (`Ctrl+Shift+J`; nếu Chrome chặn dán thì gõ `allow pasting`), dán:
   ```js
   fetch("/api/quan-tri/kiem-tra-ip",{headers:{Authorization:"Bearer "+sessionStorage.getItem("qt_token")}}).then(r=>r.json()).then(j=>console.log(JSON.stringify(j,null,2)))
   ```
   Nếu `khop_cau_hinh` là `true` và `ip_dung_cho_gioi_han` là IP công khai của bạn (không phải `169.254.x.x` hay `10.x.x.x`) thì xong. Nếu `false`, sửa `SO_PROXY_TIN_CAY` theo `goi_y`, **Apply**, chờ app khởi động lại rồi kiểm lại.
5. Bật **Health check** (bước 7c): **Configuration → tab Health check**, tick, Path `/health`, **Apply**.
6. Chụp màn hình các trang trên kèm thanh địa chỉ để đưa vào báo cáo (mục 3.7.5 và 4.1, chỗ tô vàng "chưa chạy trên máy chủ thật").

**Gặp lỗi?** Vào Web App, mở **Monitoring → Log stream** để xem lỗi.

| Hiện tượng | Nguyên nhân thường gặp | Cách sửa |
|---|---|---|
| Trang "Application Error" hoặc 503 | Sai Startup Command, hoặc thiếu `SCM_DO_BUILD_DURING_DEPLOYMENT=true` nên chưa cài thư viện | Kiểm 7a, 7b; chạy lại bước 8b |
| Log báo `could not connect`, `timeout` tới database | Chưa đánh dấu "Allow public access from any Azure service" | Bước 4, tab Networking |
| Log báo `password authentication failed` | Sai mật khẩu, hoặc mật khẩu có ký tự đặc biệt | Đặt lại mật khẩu database (chỉ chữ và số), sửa `DATABASE_URL` |
| `/san-sang` trả 503 "Kho chưa có thủ tục" | Chưa chép dữ liệu, hoặc chép vào nhầm database | Làm lại bước 5, kiểm chuỗi có `/guidance_db` |
| `RequestDisallowedByPolicy` khi tạo | Vùng không được phép | Bước 2 |
| `az postgres flexible-server firewall-rule list ... -n` báo `unrecognized arguments` | Azure CLI mới đổi tham số | Dùng `--server-name <server>` thay cho `-n` |

## 10. Theo dõi, cập nhật, dừng

- **Theo dõi:** tạo tài khoản UptimeRobot miễn phí, thêm monitor HTTP(s) tới `https://<địa-chỉ-app>/health`, chu kỳ 5 phút, để nhận email khi trang không truy cập được.
- **Xem credit còn lại:** trên portal, tìm **Education** (Education hub); trang tổng quan hiện số credit còn lại.
- **Cập nhật mã:** sửa và chạy thử trên máy trước. Đổi tên gói cũ (`ren azure_deploy.zip azure_deploy_<ngày>.zip`) để còn đường quay lại, rồi chạy lại bước 8a và 8b. Không cần chép lại dữ liệu; biến môi trường và địa chỉ giữ nguyên. Sửa **dữ liệu** trên máy thì Azure không tự cập nhật: đừng tự chạy `--xoa-dich`.
- **Tường lửa database:** quy tắc “Allow public access from any Azure service” cho phép kết nối từ mọi dịch vụ Azure, kể cả của khách hàng khác; lớp bảo vệ còn lại là mật khẩu. Quy tắc IP máy bạn chỉ cần khi chép dữ liệu, có thể xóa sau đó.
- **Dừng để khỏi tốn credit sau khi chấm:** bấm **Stop** trên Web App **không** dừng tính tiền gói B1. Muốn dừng hẳn thì vào App Service plan, đổi gói xuống **Free F1** (**Scale up**), hoặc xóa cả nhóm `rg-tracuu`. Database trên máy bạn vẫn còn nguyên.

## 11. (Tùy chọn) Gắn tên miền .id.vn

Gói B1 cho gắn tên miền riêng và cấp HTTPS miễn phí (App Service managed certificate).

1. Đăng ký `.id.vn` (miễn phí nếu bạn từ đủ 18 đến dưới 23 tuổi) qua Mắt Bão, PA Vietnam hoặc iNET.
2. Trên Web App, vào **Settings → Custom domains → Add custom domain**, chọn **App Service Managed Certificate**.
3. Azure hiện các bản ghi DNS cần tạo: một bản ghi TXT `asuid…`, cùng CNAME (cho `www`) hoặc A (cho tên miền gốc). Chép đúng các bản ghi đó vào trang quản lý DNS của nhà đăng ký, chờ vài phút rồi bấm **Validate → Add**.

## 12. Những điều không làm

- Không đưa `backend/.env`, chuỗi kết nối hay mật khẩu lên GitHub, vào báo cáo hay gửi qua chat.
- Không chạy `crawler.py` trên Azure. Dữ liệu đã chép từ máy bạn.
- Không chạy `chuyen_du_lieu.py --xoa-dich` nếu không chắc. Công cụ tự dừng khi đích đã có dữ liệu khác.

## 13. Kết quả chạy thật (24/10/2026)

Web App Linux, Python 3.12, Basic B1, East Asia; PostgreSQL flexible server 18.6, Burstable B1ms, 32 GiB.

| Kiểm tra | Kết quả |
|---|---|
| `chuyen_du_lieu.py` (Windows 10, PostgreSQL 18 → Azure) | 9.451/9.451 bản ghi, SHA-256 nội dung và thời điểm trùng: `CHÉP ĐỦ VÀ KHỚP` |
| `dong_goi_azure.py` | 41 tệp, 0,3 MB, không có `.env`, `venv`; build Oryx 0 lỗi |
| `/health` | HTTP 200, “Kết nối DB thành công” |
| `/san-sang` | `{"san_sang":true,"so_thu_tuc_cong_khai":9451}` |
| Trang công dân | 9.451 thủ tục, 15 cơ quan, 301 lĩnh vực; “làm sổ đỏ” 12 kết quả, 453 ms |
| Khu vực cán bộ | đăng nhập được, 9.451 bản ghi |
| `/api/quan-tri/kiem-tra-ip` | `so_muc` 1, `SO_PROXY_TIN_CAY` 1, `khop_cau_hinh` true |

Ảnh chụp: `bao_cao/kiem_thu_20261024/`.
