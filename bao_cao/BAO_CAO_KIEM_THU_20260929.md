# Kiểm thử độc lập starter kit mới nhất

**Đợt kiểm thử:** 28–29/09/2026. **Gói được kiểm tra:** `starter_kit (1)(1).zip`, bản 28/09 bổ sung câu hỏi tự nhiên. Đây là báo cáo kiểm tra, không phải bản sửa ứng dụng.

## 1. Nhận định

Hệ thống đã có nền tảng dùng được cho đồ án: luồng tra cứu theo tên tái lập tốt, API đáp ứng các ca chức năng đã thử, mã được tổ chức đủ rõ để tiếp tục phát triển. Tuy nhiên, **chưa nên mô tả bản mới là đã tra cứu chính xác câu hỏi tự nhiên hoặc sẵn sàng dùng như trợ lý tư vấn**.

Sửa mẫu số giúp giảm trả rỗng nhưng cũng nâng điểm những kết quả lạc đề. Các truy vấn ngoài phạm vi có thể nhận kết quả 80–100%. Bên cạnh đó, cùng chữ tiếng Việt được mã hóa ở hai dạng Unicode tương đương cho kết quả khác; bộ đo mới chưa chặn một số lỗi gán nhãn. Đây là các ưu tiên trước khi mở rộng AI.

Mã ứng dụng trong gói nhận được giữ nguyên: đã đối chiếu toàn bộ file với ZIP sau kiểm thử, không có file nội dung bị thay. Chỉ tạo script, báo cáo và database kiểm thử riêng.

## 2. Đã chạy những gì, ở đâu

| Hạng mục | Phương pháp | Kết quả/phạm vi |
|---|---|---|
| Xác minh gói | Kiểm tra danh mục, SHA256, khác biệt với bản trước, mục 9 | Đúng bản sửa mẫu số; mục 9 giữ nguyên |
| A/B/C chính | Gọi nguyên `danh_gia.py`, 500 câu/nhóm, trước và sau | 1.500/1.500 truy vấn có cùng danh sách ID, điểm và phần trăm |
| Đề bổ sung | A/B với 3 seed; B có dấu, 500 câu/bộ | 3.500 truy vấn; thứ hạng ID đáp án không đổi |
| Câu hỏi tự nhiên | Gọi nguyên `danh_gia_tu_nhien.py`, 50 câu trước/sau | Báo cáo khớp file kèm gói; rỗng 7 → 0; chưa có nhãn đúng |
| Tái lập giữa tiến trình | Chạy bộ TN với PYTHONHASHSEED=17 và 93 | Hai báo cáo khớp từng byte với báo cáo TN mới |
| Unicode | Chuyển 50 câu NFC sang NFD, giữ cùng nội dung chữ | 44/50 danh sách ID kết quả thay đổi |
| Tình huống truy vấn | 8 truy vấn chẩn đoán; 300 đoạn tên thêm một từ ngoài kho | Có phản ví dụ lạc đề; 300 ca chưa thấy mất ID từng được trả về |
| API | FastAPI thực qua ASGI, SQLAlchemy + SQLite tạm với 9.451 bản ghi thật | 25 kiểm tra chức năng đạt; 1 kiểm tra tái hiện giới hạn cache |
| Đồng thời | Nằm trong kiểm tra API: 32 yêu cầu tra cứu đồng thời | Kết quả giống từng yêu cầu chạy riêng |
| Server HTTP | Uvicorn thực, 19 yêu cầu HTTP, tối đa 8 luồng client | Tất cả trả 200; gồm trang HTML và các endpoint được chọn |
| Crawler | 9 kịch bản mạng/XML giả lập; DB SQLite tạm | Các ca retry/commit/trùng mã/cursor được xử lý như mong đợi; phát hiện thêm lỗi nghiệp vụ XML ở ca riêng |
| Bộ đo tự nhiên | 9 ca kiểm tra phép tính và đầu vào CSV | Phép tính thông thường đúng; phát hiện lỗi dữ liệu đầu vào |
| Frontend | Node chạy JavaScript thật với DOM/fetch mẫu | Luồng tiền/escape/request cũ đạt; tái hiện lỗi khởi động và dữ liệu cấu trúc |
| Parser | XML mẫu để kiểm tra giới hạn chuyển đổi | Xác nhận mất attributes/mixed content và giới hạn namespace; không kết luận dữ liệu thật đã bị mất |

**Môi trường:** Linux, Python 3.12, Node; thư viện backend theo requirements của gói. Không có PostgreSQL 18/Windows của sinh viên trong môi trường này. Kiểu JSONB chỉ được thay bằng JSON trong tiến trình thử SQLite, không sửa model bàn giao.

Phép đo thuật toán đọc đúng các bản ghi trong JSON thật bằng adapter chỉ đọc; gọi mã search và bộ đo thật, không mô phỏng công thức xếp hạng. Corpus gồm 9.451 thủ tục, 15 cơ quan, 301 lĩnh vực. Không dùng kho giả để chọn hay đánh giá thuật toán. Mẫu giả lập chỉ phục vụ kiểm tra chức năng riêng của crawler, parser, giao diện và phép tính bộ đo.

**Giới hạn:** chưa chạy API crawl thật; chưa đối chiếu nội dung `data`/XML thật; chưa kiểm tra trực quan trên Windows. Trình duyệt kiểm thử không mở được địa chỉ localhost (`ERR_BLOCKED_BY_CLIENT`), còn bộ cài Chromium tải về không sử dụng được. Vì thế không xác nhận bố cục, font, responsive hoặc thao tác trình duyệt bằng kết quả DOM mẫu. Việc kiểm tra HTTP thành công không thay thế kiểm tra trực quan.

## 3. Chất lượng tra cứu: kết quả đo lại

Ở bảng này, “trước” là bản tăng điểm cụm 1,3, “sau” là bản bổ sung sửa mẫu số. Không nhầm với mốc cũ hơn có B Top-1 69%.

| Nhóm, 500 câu | Top-1 trước → sau | Top-5 trước → sau | MRR trước → sau | Không thấy ID trước → sau |
|---|---:|---:|---:|---:|
| A | 90,8% → 90,8% | 99,8% → 99,8% | 0,949750 → 0,949750 | 0% → 0% |
| B | 72,0% → 72,0% | 97,2% → 97,2% | 0,826879 → 0,826879 | 0% → 0% |
| C | 21,6% → 21,6% | 49,2% → 49,2% | 0,342031 → 0,342031 | 20,2% → 20,2% |

Báo cáo chính trước/sau giống nhau sau khi bỏ dòng SHA search.py; bản sau khớp báo cáo kèm gói. Nhóm C chỉ tham khảo.

| Bộ bổ sung | Số câu | Top-1 trước → sau | Số ID đáp án đổi hạng |
|---|---:|---:|---:|
| A, seed 777 | 500 | 92,0% → 92,0% | 0 |
| B, seed 777 | 500 | 70,4% → 70,4% | 0 |
| A, seed 31337 | 500 | 90,4% → 90,4% | 0 |
| B, seed 31337 | 500 | 73,8% → 73,8% | 0 |
| A, seed 424242 | 500 | 92,0% → 92,0% | 0 |
| B, seed 424242 | 500 | 70,0% → 70,0% | 0 |
| B có dấu, seed 5555 | 500 | 74,2% → 74,2% | 0 |

Tổng 5.000 truy vấn trên hai phiên bản, tức 10.000 lượt tìm kiếm trong các bộ đối chiếu này. Các bộ bổ sung dùng seed khác nhưng **không bảo đảm tách toàn bộ ID/chủ đề** khỏi bộ chính; không gọi đây là 5.000 truy vấn độc lập có nhãn người dùng.

50 câu tự nhiên vẫn chưa gán nhãn: chỉ xác nhận được số câu rỗng 7/50 → 0/50. Không xác nhận Top-1 tự nhiên 78% là độ chính xác chính thức. Phép xấp xỉ khớp khái niệm trong tài liệu không thay thế nhãn thủ tục đúng.

300 đoạn tên có thêm từ ngoài kho chưa cho thấy trường hợp mất ID từng được trả về. Đây là kiểm tra bổ sung hữu hạn, không chứng minh mọi truy vấn đều không xấu đi.

## 4. Các vấn đề ưu tiên cao

### R1 — Kết quả lạc đề được đẩy lên phần trăm rất cao

**Mức độ: cao đối với độ tin cậy của tra cứu. Có bằng chứng trên corpus thật.**

| Truy vấn | Trước sửa mẫu số | Sau sửa mẫu số, kết quả đầu |
|---|---|---|
| `xin visa` | Rỗng | Thủ tục về đăng ký lưu hành vắc xin Covid-19 — 100% |
| `cách nấu phở bò` | Rỗng | Xét đặc cách tốt nghiệp trung học phổ thông — 84% |
| `hôm nay trời có mưa không` | Rỗng | Thủ tục đưa người có công về nuôi dưỡng tại gia đình — 100% |
| `mua điện thoại iPhone ở đâu` | Rỗng | Đăng ký hình thức tra cứu thông tin hóa đơn điện tử — 80% |
| `xin cấp sổ đỏ lần đầu` | Khám giám định lần đầu do bệnh nghề nghiệp — 31% | Cùng thủ tục — 51% |
| `xin giấy phép kinh doanh karaoke` | Giấy phép kinh doanh vận chuyển hàng không — 41% | Cùng thủ tục — 100% |

Nguyên nhân đọc từ mã và kết quả đo: các đơn vị không có trong kho bị bỏ khỏi mẫu số, nên vài đơn vị thông dụng còn lại có thể chiếm gần toàn bộ thang điểm. Ví dụ `xin visa` còn khớp âm tiết `xin` trong `vắc xin`. Đây là quy tắc tổng quát của hệ thống, không nên sửa bằng blacklist các câu trong bảng.

Khuyến nghị: bổ sung nhóm truy vấn ngoài phạm vi và nhóm nhầm chủ đề vào bộ đề có nhãn; đo khả năng từ chối và độ đúng của kết quả đầu. Cân nhắc giao diện hiển thị “điểm khớp từ khóa” thay vì phần trăm dễ hiểu thành độ chắc chắn, hoặc tạm ẩn số phần trăm. Nếu đổi cách xét ứng viên/ngưỡng, phải đo lại A/B trước/sau và các nhóm mới.

### R2 — Unicode tương đương cho kết quả khác

**Mức độ: cao; vấn đề đã được tài liệu nhắc nhưng nay có số đo tái hiện.**

Cả 50 câu gốc đều ở NFC. Khi chuyển sang NFD bằng `unicodedata.normalize`, 44/50 câu thay đổi danh sách ID trả về dù nội dung chữ tương đương. Ví dụ:

- `làm hộ chiếu cần những gì`: 27 kết quả → 6 kết quả; kết quả đầu từ 100% → 45%.
- `hộ chiếu hết hạn thì làm lại thế nào`: 34 kết quả → 2 kết quả.

Vị trí: `app/search.py`, `norm_dau()`. Regex chạy trước bước đưa chuỗi về NFC nên các dấu tổ hợp có thể trở thành khoảng trắng, làm hỏng âm tiết ở nhánh có dấu. Đây là phép thử tính nhất quán, **44/50 không có nghĩa 44 câu tìm sai** vì chưa có nhãn.

Khuyến nghị: chuẩn hóa Unicode thống nhất ở đầu vào và khi dựng chỉ mục, thử nghiệm trên nhánh riêng; kiểm tra NFC/NFD cho cùng kết quả. Đánh giá cả truy vấn có dấu/không dấu, A/B và nhóm tự nhiên trước khi giữ thay đổi. Chưa sửa trong đợt kiểm thử.

### R3 — Bộ đo tự nhiên chưa bảo vệ đủ tính đúng của nhãn

**Mức độ: cao đối với độ tin cậy số liệu báo cáo; lỗi xử lý đầu vào.**

Vị trí: `backend/danh_gia_tu_nhien.py`, `doc_bo_de()` và `main()`.

| Đầu vào kiểm thử | Hành vi thực tế |
|---|---|
| Có đủ cột nhưng mọi `cau_hoi` rỗng | `ZeroDivisionError` khi tính tỷ lệ rỗng trên 0 câu |
| CSV chỉ có dòng tiêu đề đúng | Báo thiếu cột dù cột có tồn tại |
| Nhãn `INVALID_CODE` | Cảnh báo rồi bỏ nhãn; dòng thành “chưa gán”, chương trình vẫn trả mã thoát 0 |
| Nhãn `KHONG_CO; <mã hợp lệ>` | Âm thầm chấm theo mã hợp lệ, không báo nhãn tự mâu thuẫn |
| Hai dòng trùng STT và cùng câu | Cả hai cùng được tính; không cảnh báo |

Phép tính Top-1/Top-5/MRR trên đầu vào hợp lệ đã qua kiểm tra riêng: 4 kết quả có thứ hạng [1,3,không thấy,không thấy] cho Top-1 25%, Top-5 50%, MRR 0,333333. Nhiều mã đúng và nhóm KHONG_CO cũng cho kết quả mong đợi trong ca thử. Các ca này dùng kết quả fixture để kiểm tra phép tính, không phải số đo chất lượng tra cứu.

Khuyến nghị: kiểm tra toàn bộ bộ đề trước khi tính; phân biệt nhãn chưa gán với nhãn không hợp lệ; chặn nhãn mâu thuẫn; xử lý bộ đề rỗng; cảnh báo STT/câu trùng. Khi mở Excel, đặt cột mã thủ tục kiểu văn bản để giữ đúng mã. Cố định nhãn và SHA trước khi so sánh thuật toán.

## 5. Crawler, dữ liệu và giao diện

### R4 — XML báo lỗi có thể bị coi là thu đủ 0 bản ghi

**Mức độ: trung bình; ca kiểm thử giao thức giả lập, chưa biết API thật có trả đúng dạng này không.**

Cho `fetch_page()` trả HTTP thành công với XML chứa `ErrorCode=FAILED`, thông báo không được phép và `TongSoBanGhi=0`. Crawler trả `failed=False`, `matched_total=True`, lý do “API không trả thêm thủ tục”. `print_report()` sẽ xếp ca này vào “KHỚP SỐ LƯỢNG”.

Vị trí: `crawler.py`, `crawl_agency()` đọc danh sách/tổng nhưng không xác nhận thành công nghiệp vụ từ envelope. Cần đối chiếu quy ước phản hồi thành công/lỗi của API thật rồi thêm kiểm tra, không tự đoán mã thành công. Không có thao tác xóa dữ liệu trong ca thử này.

Các ca đã đạt: mã lặp trong cùng trang; trang sau lỗi vẫn giữ trang trước đã commit; không rõ tổng không báo đủ; 401 lấy lại token; cursor lặp; thiếu mã; DB đã có mã trùng; XML hỏng; tổng đổi giữa trang. Chưa xác nhận toàn bộ quá trình crawl thật hay cơ quan còn thiếu.

### R5 — Phản hồi khởi động chậm làm đóng trang chi tiết đang xem

**Mức độ: trung bình; tái hiện bằng JavaScript thật và DOM/fetch mẫu.**

Thứ tự tái hiện: stats/filters còn chờ → người dùng tra cứu → mở chi tiết thành công → stats/filters trả xong → callback `DOMContentLoaded` gọi `run()` → chi tiết bị ẩn, danh sách hiện lại. Bộ đếm request hiện có không bảo vệ bước khởi động này.

Vị trí: `frontend/index.html`, callback `DOMContentLoaded`. Nên tránh để lần nạp đầu thay trạng thái điều hướng mà người dùng đã chọn. Cần kiểm tra thêm trực tiếp bằng mạng chậm trên trình duyệt Windows.

### R6 — Trường có cấu trúc con có thể hiện `[object Object]`

**Mức độ: trung bình, phụ thuộc cấu trúc dữ liệu; chưa có XML thật để xác định tần suất.**

`YeuCauDieuKien` là object thì `docView()` gọi `txt()` và hiển thị `[object Object]`, không hiện nội dung con. Mảng hỗn hợp object/chuỗi trong `rawView()` cũng có dòng như vậy. Khối JSON đầy đủ vẫn chứa nội dung, nên không kết luận database bị mất dữ liệu từ lỗi trình bày này.

Khuyến nghị: khi dữ liệu vượt kiểu đã hỗ trợ, dùng bộ dựng cấu trúc đệ quy hoặc fallback rõ ràng sang giá trị nguồn. Không dịch, gộp hay tự suy nội dung ở parser.

### R7 — Các giới hạn dữ liệu đã xác nhận bằng ca mẫu

- Parser giữ được các thẻ lặp đơn giản theo thứ tự; nhưng bỏ thuộc tính XML, phần text trước/sau thẻ con và danh tính namespace. Với `<MoTa>Đầu <b>giữa</b> cuối</MoTa>`, chỉ còn `{"b":"giữa"}`.
- `extract_total()` và `extract_last_id()` dùng regex tên thẻ không namespace; `<n:TongSoBanGhi>`/`<n:LastId>` không được nhận ra.
- Khóa trùng VO_BOC như `Object` ở cấp thủ tục bị loại. Cần XML thật xác định đây có thực sự là dữ liệu nghiệp vụ không.
- Sửa SQL giữ nguyên `updated_at` làm kết quả search còn tên cũ trong khi endpoint chi tiết đã trả tên mới. Cơ chế cache hiện tại có giới hạn này đúng như tài liệu.
- Schema chưa có unique constraint cho mã thủ tục; chưa thử hai crawler đồng thời. Không coi việc xử lý mã lặp trong một trang là bằng chứng an toàn khi chạy đồng thời.

Giữ nguyên mục 9: chưa sửa parser hoặc tự gộp dữ liệu. Cần mẫu XML thật và tiêu chí bảo toàn rõ ràng trước khi thay đổi.

## 6. Những phần đang hoạt động tốt trong phạm vi thử

API từ chối limit/offset/q ngoài giới hạn, trả 404 cho ID không tồn tại, phân trang không trùng hai trang đầu, thống kê đúng 9.451/15/301. Bộ lọc vẫn chấm toàn kho trước lọc; query `cấp` + Bộ Công an trả 60 kết quả đúng tập xếp hạng đã kiểm tra. Cache nạp lại khi nội dung đổi với mốc cập nhật mới. 32 yêu cầu đồng thời trả kết quả giống chạy riêng.

Giao diện đã phân biệt thiếu tiền với 0, giữ chuỗi số nguyên lớn không bị làm tròn, giữ mô tả mức thu; hiển thị nhiều phí/thời hạn theo ngữ cảnh. Các ca escape HTML, phản hồi search cũ, quay về danh sách khi chi tiết đang tải và HTTP lỗi đã đạt trong kiểm thử JavaScript.

Thời gian trực tiếp hàm search trên bộ chính trong môi trường này: trung vị trước/sau khoảng 25,41/25,17 ms; p95 khoảng 57,08/57,09 ms. Đây là phép đo hỗ trợ, không phải benchmark Windows hay cam kết tốc độ; có tải kiểm thử khác chạy cùng lúc.

## 7. Điểm cần sửa trong tài liệu

- Báo cáo diễn giải nói câu kết hôn với người nước ngoài sau sửa có 10 kết quả, thủ tục phù hợp đứng đầu. Báo cáo thô và chạy lại thực tế có 11 kết quả, đầu bảng là thủ tục cho công dân Việt Nam tạm trú ở nước ngoài. Phải dùng kết quả chạy thực tế khi viết báo cáo.
- Diễn đạt “4 bộ đề kiểm tra thêm, 3.500 truy vấn” không rõ: thực tế đối chiếu 6 bộ A/B theo 3 seed và 1 bộ B có dấu, mỗi bộ 500. Nên ghi rõ 7 bộ, tổng 3.500.
- “Điểm xếp hạng không đổi” không có nghĩa danh sách trả về luôn không đổi: thay mẫu số làm thay đổi việc vượt ngưỡng, nhánh chính/gợi ý và số lượng kết quả. Tránh phát biểu tuyệt đối “không câu nào xấu đi” ngoài các mẫu đã kiểm tra.
- SHA file CSV dạng byte có thể khác SHA do bộ đo chuẩn hóa BOM/xuống dòng; trường hợp gói này không phải lỗi nhầm bộ đề. Bộ đo báo SHA `fad16617…`, đúng sau chuẩn hóa.

## 8. Lời khuyên và thứ tự thực hiện

1. **Sửa độ tin cậy công cụ đo trước.** Chặn CSV/nhãn không hợp lệ; đính chính ví dụ tài liệu. Việc này giúp các lần đo tiếp theo không tự loại câu khó khỏi mẫu số do gán sai mã.
2. **Gán nhãn bộ 50 câu, bổ sung truy vấn ngoài phạm vi và câu cần hỏi lại.** Đọc thủ tục và điều kiện để chọn mã; không lấy kết quả đầu của chính hệ thống làm đáp án. Chưa chắc thì đánh dấu để rà soát, không gán KHONG_CO chỉ vì search chưa tìm thấy. Tách bộ dùng tinh chỉnh khỏi bộ kiểm tra cuối.
3. **Xử lý Unicode theo một quy tắc chung**, đo trước/sau bằng A/B/C và bộ có dấu/NFD. Không sửa riêng câu hộ chiếu.
4. **Đánh giá lại sửa mẫu số và cách hiển thị điểm.** Đặt cạnh nhau khả năng tìm đúng, từ chối truy vấn ngoài phạm vi và số kết quả lạc đề. Không chọn phương án chỉ vì trả rỗng giảm.
5. **Chốt dữ liệu trước AI:** kiểm tra lỗi nghiệp vụ crawler, lấy vài XML thật phức tạp để đối chiếu, sửa lỗi giao diện trạng thái/kiểu dữ liệu. Sau đó mới mở rộng đồng nghĩa hoặc RAG.

Về quy tắc chấp nhận: bản sửa mẫu số **giữ nguyên B, không làm B tăng**. Vì vậy không nên ghi rằng thay đổi này đã đáp ứng đúng điều kiện ban đầu “B tăng, A không giảm”. Bộ A/B lấy câu từ tiêu đề nên có điểm mù đối với lỗi tự nhiên/ngoài phạm vi. Có thể đề xuất thêm tiêu chí dành riêng cho nhóm tự nhiên có nhãn và truy vấn ngoài phạm vi; chỉ thay quy tắc khi sinh viên xác nhận. Đợt kiểm thử không tự đổi tiêu chí, thuật toán hoặc hoàn tác bản đang dùng.

Gợi ý phân bổ từ 29/09: 1–2 ngày chốt bộ đo và tài liệu; 2–3 ngày gán nhãn/đối chiếu XML; tuần tiếp theo thử nghiệm Unicode, độ khớp và đồng nghĩa có kiểm chứng. Chốt phạm vi AI với người hướng dẫn trước khi dành tuần 08–14/10 cho prototype. Giữ 15–21/10 cho kiểm thử trên Windows, báo cáo, demo và dự phòng.

## 9. Xác nhận trên máy Windows

Đây là các lệnh đo trên bản bạn đã cài, không chép mã kiểm thử đè vào backend. Mở CMD:

```bat
cd /d C:\Users\Admin\Downloads\starter_kit\starter\backend
venv\Scripts\activate
python danh_gia.py 500 --luu bao_cao_ABC_xac_nhan_20260929.txt
python danh_gia_tu_nhien.py --luu bao_cao_TN_xac_nhan_20260929.txt
```

Không cần bật server để chạy hai bộ đo; không crawl giữa các lần so sánh. Nếu vừa chép backend mới, tại cửa sổ server nhấn Ctrl+C, rồi trong CMD đã kích hoạt venv chạy:

```bat
uvicorn app.main:app
```

Mở frontend và Ctrl+F5. Chỉ kỳ vọng A 90,8%, B 72,0% và rỗng tự nhiên 0/50 khi mã bộ đo, kho, bộ đề và search.py tương ứng với gói đã kiểm tra. Các nhãn mới sẽ thay SHA bộ đề và cần chạy lại cả hai phiên bản khi so sánh.

## 10. Bằng chứng và định danh

Gói `BANG_CHUNG_KIEM_THU_20260929.zip` chứa bản nguồn đã kiểm tra, corpus xuất thật, script kiểm thử đầy đủ, báo cáo/trace và README chạy lại. Không có `.env`, venv, DB người dùng hoặc tài khoản API. Các SQLite thử nghiệm không được đóng gói; script tạo lại khi chạy.

| Thành phần | SHA256 |
|---|---|
| search trước | `30c851204305b9aa5811c8a8260392001369cb39f510bdd87fc5eb18e4c7f9fc` |
| search sau | `1d82cbd76bdcc19c1f5d469b03e79d87ba021468c7e9b22b1f65d1b65bbedbb2` |
| Bộ đo ABC | `a96e9ef5fbba8e34e630e37e464112cb2532742335ea57851d1fe9cace7b904f` |
| Bộ đo TN | `d8e38a80fd8571cf327f80fbdb78c0dd5d4ff5d1f877e08bd178f83338cf33ee` |
| Kho tra cứu theo bộ đo | `2319b44b115bce195082764a04cdfa64ab6765bd6d559537b2583b951f8de685` |

Bằng chứng chính trong thư mục `audit_20260928/results`: `retrieval_summary.json`, `abc_before.txt`, `abc_after.txt`, `abc_trace.json`, `tn_before.txt`, `tn_after.txt`, `natural_trace.json`, `api_checks.json`, `http_checks.json`, `evaluator_checks.json`, `parser_crawler_diagnostics.json`, `frontend_edge_checks.json` và các log. Thư mục giữ tên 20260928 vì đợt thử bắt đầu ngày đó; báo cáo được hoàn tất ngày 29/09.
