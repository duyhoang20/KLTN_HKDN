"""
Crawler lấy dữ liệu thủ tục hành chính thật từ API Cổng Dịch vụ công,
rồi nạp vào database.

Cách chạy:
    python crawler.py            # lấy mặc định các Bộ trong danh sách AGENCY_CODES
    python crawler.py G01        # chỉ lấy 1 Bộ cụ thể (để test)

Cơ chế:
  1. Tự động lấy token từ API đăng nhập (không cần copy tay).
  2. Với mỗi mã cơ quan, lặp phân trang (dùng LastId) đến khi lấy hết.
  3. Ánh xạ XML -> cấu trúc DB, nạp vào bảng guidance_documents (tránh trùng theo mã thủ tục).

BẢO MẬT: username/password đọc từ file .env, KHÔNG viết cứng trong code.
File .env tuyệt đối không đưa lên GitHub / không gửi cho ai.
"""
import os
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
import urllib.parse
import urllib.request

from dotenv import load_dotenv

# cho phép import các module trong app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal, engine, Base
from app import models
from app.xml_parser import parse_procedures, extract_last_id, extract_total

load_dotenv(Path(__file__).resolve().parent / ".env")

TOKEN_URL = os.getenv("DVC_TOKEN_URL")
CLIENT_ID = os.getenv("DVC_CLIENT_ID") or "web-onegate"   # để trống trong .env thì dùng giá trị mặc định
USERNAME = os.getenv("DVC_USERNAME")
PASSWORD = os.getenv("DVC_PASSWORD")
PROCEDURES_URL = os.getenv("DVC_PROCEDURES_URL")

# Số thủ tục lấy mỗi lần gọi API.
# Để 25 cho an toàn: lấy ít mỗi lần -> phản hồi nhanh, ít bị timeout.
# Nếu mạng khỏe và muốn nhanh hơn, có thể tăng lên 50 hoặc 100.
LIMIT = 25

# Danh sách mã Bộ (cấp 1, bắt đầu bằng G) - theo QĐ 09/2025/QĐ-TTg
# Mặc định lấy tất cả các Bộ. Muốn test 1 Bộ thì truyền tham số dòng lệnh.
AGENCY_NAMES = {
    "G01": "Bộ Công an",
    "G02": "Bộ Công Thương",
    "G03": "Bộ Giáo dục và Đào tạo",
    "G06": "Bộ Khoa học và Công nghệ",
    "G08": "Bộ Ngoại giao",
    "G09": "Bộ Nội vụ",
    "G10": "Bộ Nông nghiệp và Môi trường",
    "G11": "Bộ Quốc phòng",
    "G12": "Bộ Tài chính",
    "G15": "Bộ Tư pháp",
    "G16": "Bộ Văn hóa, Thể thao và Du lịch",
    "G17": "Bộ Xây dựng",
    "G18": "Bộ Y tế",
    "G19": "Ngân hàng Nhà nước Việt Nam",
    "G20": "Thanh tra Chính phủ",
    "G21": "Bộ Dân tộc và Tôn giáo",
}

AGENCY_CODES = list(AGENCY_NAMES.keys())


def get_token():
    """Tự động lấy access_token từ API đăng nhập."""
    if not (TOKEN_URL and PROCEDURES_URL and USERNAME and PASSWORD):
        raise SystemExit(
            "LỖI: cần DVC_TOKEN_URL, DVC_PROCEDURES_URL, DVC_USERNAME và DVC_PASSWORD trong .env.\n"
            "Hãy copy .env.example thành .env rồi điền thông tin đăng nhập."
        )
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "username": USERNAME,
        "password": PASSWORD,
        "grant_type": "password",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        import json
        result = json.loads(resp.read())
    return result["access_token"]


def fetch_page(token, agency_code, last_id="", retries=4):
    """
    Gọi API lấy 1 trang thủ tục. Trả về chuỗi XML.
    Tự động thử lại nhiều lần nếu mạng chậm / API phản hồi lâu (timeout),
    mỗi lần chờ lâu hơn một chút trước khi thử lại.
    """
    params = urllib.parse.urlencode({
        "agency-code": agency_code,
        "last-id": last_id,
        "limit": LIMIT,
        "keyword": "",
        "procedure-codes": "",
    })
    url = f"{PROCEDURES_URL}?{params}"

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError:
            raise  # lỗi HTTP (401, 403...) xử lý riêng ở nơi gọi
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = attempt * 5  # chờ 5s, 10s, 15s rồi thử lại
                print(f"    (mạng chậm, thử lại lần {attempt + 1}/{retries} sau {wait}s...)")
                time.sleep(wait)
    raise last_error


def doc_vo_phan_hoi(xml):
    """Trả về ErrorCode/Message nguyên văn trong phản hồi (nếu có), để in ra.

    Chỉ đọc lại, KHÔNG diễn giải thành công/thất bại, vì chưa có tài liệu
    quy ước mã lỗi của API. Chấp nhận tiền tố namespace (vd. <n:ErrorCode>).
    """
    phan = []
    for the in ("ErrorCode", "Message"):
        m = re.search(rf"<(?:[\w.-]+:)?{the}>(.*?)</(?:[\w.-]+:)?{the}>", xml or "", re.DOTALL)
        if m and m.group(1).strip():
            phan.append(f"{the}={m.group(1).strip()[:200]}")
    return "; ".join(phan)


@dataclass
class CrawlResult:
    code: str
    token: str = field(repr=False)
    expected: int | None = None
    new: int = 0
    updated: int = 0
    committed_codes: set = field(default_factory=set)
    reason: str = ""
    failed: bool = False
    envelope: str = ""   # ErrorCode/Message nguyên văn của trang đầu, nếu có

    @property
    def matched_total(self):
        # Không kết luận "khớp" khi không nhận được bản ghi nào: tổng bằng 0
        # có thể là cơ quan không có thủ tục, nhưng cũng có thể là API báo lỗi
        # nghiệp vụ (sai quyền, sai tham số) kèm TongSoBanGhi=0. Không đoán mã
        # thành công của API; để người vận hành đối chiếu phần vỏ phản hồi.
        return (not self.failed and self.expected is not None
                and self.expected > 0
                and len(self.committed_codes) == self.expected)


def crawl_agency(token, agency_code, db):
    """Commit theo trang; báo cáo chỉ đếm mã đã commit trong lần chạy này.

    Không đoán con trỏ kế tiếp khi trang lỗi. Dừng cơ quan đang chạy và
    báo chưa xác minh đủ, giữ nguyên các trang trước đã commit.
    """
    result = CrawlResult(agency_code, token)
    print(f"\n=== {agency_code}: {AGENCY_NAMES.get(agency_code, agency_code)} ===")
    last_id = ""
    cursors = {last_id}
    page = 0
    while True:
        page += 1
        try:
            try:
                xml = fetch_page(result.token, agency_code, last_id)
            except urllib.error.HTTPError as exc:
                if exc.code != 401:
                    raise
                result.token = get_token()
                xml = fetch_page(result.token, agency_code, last_id)
            try:
                procs = parse_procedures(xml)
            except Exception:
                # Chỉ thử lại cùng con trỏ một lần; không bỏ qua trang âm thầm.
                result.token = get_token()
                xml = fetch_page(result.token, agency_code, last_id)
                procs = parse_procedures(xml)
            if page == 1:
                result.envelope = doc_vo_phan_hoi(xml)
            total = extract_total(xml)
            if result.expected is None:
                result.expected = total
            elif total is not None and total != result.expected:
                raise ValueError("Tổng số API thay đổi giữa các trang; cần chạy lại để đối chiếu.")
            if not procs:
                if not result.committed_codes:
                    result.reason = ("API trả 0 thủ tục ngay từ đầu; chưa thể xác minh. "
                                     "Kiểm tra quyền tài khoản/mã cơ quan."
                                     + (f" Vỏ phản hồi: {result.envelope}" if result.envelope else ""))
                else:
                    result.reason = "API không trả thêm thủ tục."
                break
            if any(not p.get("procedure_code") for p in procs):
                raise ValueError("Trang có thủ tục thiếu mã; chưa lưu trang để tránh tạo trùng khi chạy lại.")

            new_page = updated_page = 0
            page_codes = set()
            for proc in procs:
                code = proc["procedure_code"]
                # Nếu DB đã trùng mã, one_or_none báo lỗi để kiểm tra, không
                # tùy ý cập nhật bản ghi đầu tiên hoặc tự gộp dữ liệu.
                existing = (db.query(models.GuidanceDocument)
                            .filter(models.GuidanceDocument.procedure_code == code)
                            .one_or_none())
                if existing is None:
                    db.add(models.GuidanceDocument(**proc))
                    # Session có autoflush=False: flush để bản ghi lặp mã
                    # trong cùng trang nhìn thấy lần thêm trước đó.
                    db.flush()
                    new_page += 1
                else:
                    # Cập nhật NỘI DUNG từ nguồn nhưng GIỮ quyết định công khai
                    # của cán bộ (cột status: published / draft / archived).
                    # Trạng thái áp dụng của Cổng (ACTIVE/INACTIVE) vẫn nằm
                    # nguyên trong data["TrangThai"]; hai thứ là hai dữ kiện riêng.
                    # (Sửa 09/10/2026: trước đây crawl lại công khai lại cả bản
                    # cán bộ đã lưu trữ.)
                    for key, value in proc.items():
                        if key == "status":
                            continue
                        setattr(existing, key, value)
                    updated_page += 1
                page_codes.add(code)
            db.commit()
            result.new += new_page
            result.updated += updated_page
            result.committed_codes.update(page_codes)
            print(f"  Trang {page}: thêm {new_page}, cập nhật {updated_page}; "
                  f"{len(result.committed_codes)} mã khác nhau đã commit.")

            if result.expected is not None and len(result.committed_codes) >= result.expected:
                result.reason = "Đã đối chiếu số mã với tổng API của lần chạy."
                break
            next_id = extract_last_id(xml)
            if not next_id:
                result.reason = "Không có LastId kế tiếp."
                break
            if next_id in cursors:
                raise ValueError("LastId lặp; dừng để tránh vòng lặp vô hạn.")
            cursors.add(next_id)
            last_id = next_id
            time.sleep(0.3)
        except Exception as exc:
            db.rollback()
            result.failed = True
            result.reason = f"Trang {page}: {type(exc).__name__}: {exc}"
            break
    print("  " + result.reason)
    return result


def print_report(results):
    print("\n" + "=" * 84)
    print("ĐỐI CHIẾU LẦN THU THẬP NÀY — không phải kiểm kê toàn bộ DB")
    print(f"{'Mã':<6}{'Mã đã commit':>14}{'API báo':>12}{'Còn thiếu':>12}  Kết luận")
    for r in results:
        actual = len(r.committed_codes)
        expected = str(r.expected) if r.expected is not None else "?"
        missing = str(max(0, r.expected-actual)) if r.expected is not None else "?"
        if r.matched_total:
            status = "KHỚP SỐ LƯỢNG"
        elif not r.failed and not r.committed_codes:
            status = "0 BẢN GHI — CẦN KIỂM TRA"
        else:
            status = "CHƯA XÁC MINH ĐỦ"
        print(f"{r.code:<6}{actual:>14}{expected:>12}{missing:>12}  {status}")
        print(f"      Lượt thêm: {r.new}; lượt cập nhật: {r.updated}. {r.reason}")
    complete = bool(results) and all(r.matched_total for r in results)
    print("Các cơ quan trong phạm vi chạy đều khớp số lượng API."
          if complete else "Còn cơ quan chưa xác minh đủ; xem từng dòng phía trên.")
    print("Khớp số lượng không chứng minh mọi trường XML được bảo toàn.")
    print("Không tự xóa bản ghi cũ nếu nguồn không còn trả về.")
    return complete


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Cách dùng: python crawler.py [mã_cơ_quan]")
    codes = [sys.argv[1].upper()] if len(sys.argv) == 2 else AGENCY_CODES
    if any(code not in AGENCY_NAMES for code in codes):
        raise SystemExit("Mã cơ quan không hợp lệ. Các mã: " + ", ".join(AGENCY_CODES))
    Base.metadata.create_all(bind=engine)
    token = get_token()
    db = SessionLocal()
    try:
        results = []
        for code in codes:
            result = crawl_agency(token, code, db)
            token = result.token  # giữ token vừa làm mới cho cơ quan tiếp theo
            results.append(result)
        return 0 if print_report(results) else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
