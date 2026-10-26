"""Kiểm thử GIAO DIỆN tự động bằng trình duyệt (bổ sung 14/10/2026, TÙY CHỌN).

Vì sao có tệp này: đợt 14/10 báo “70/70 phép kiểm tra trình duyệt” nhưng không kèm
mã kiểm thử, nên không ai chạy lại được. Tệp này là bộ kiểm thử đó ở dạng chạy
được trên chính máy của bạn, với dữ liệu thật trong PostgreSQL.

Cài một lần (khoảng 150 MB, cần mạng):
    pip install playwright
    python -m playwright install chromium

Chạy (server phải đang chạy ở cửa sổ khác):
    python kiem_thu_giao_dien.py
    python kiem_thu_giao_dien.py --tk canbo --mk <mật khẩu cán bộ>  --luu ket_qua_giao_dien.txt
Không ghi gì vào database ngoài nhật ký tra cứu (vài lượt hỏi thử) và một dòng “đăng nhập” trong lịch sử
thao tác của cán bộ. Các thao tác lưu ở D4–D8 bị chặn trong trình duyệt. Không cần mô hình ngôn ngữ.
"""
import argparse
import asyncio
import json
import re
import sys
import urllib.parse
import urllib.request

KQ = []
# Sửa 21/10 bản 2 (N01): mẫu chặn URL bằng biểu thức chính quy, bắt cả /api/quan-tri/thu-tuc,
# /api/quan-tri/thu-tuc/<id> và đường có query. Mẫu glob “**/thu-tuc**” không khớp đường có /<id>
# trên một số phiên bản Playwright, làm yêu cầu giả lọt tới máy chủ thật.
CHAN_THU_TUC = re.compile(r".*/api/quan-tri/thu-tuc(/\d+)?(\?.*)?$")


def thu(ten, dat, thuc_te=""):
    KQ.append((ten, bool(dat), thuc_te))
    print(("  ĐẠT   " if dat else "  TRƯỢT ") + ten + ("" if dat else f"  ← {str(thuc_te)[:160]}"))


def lay(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def tim_thu_tuc_co_ho_so(base):
    """Tìm một thủ tục có ít nhất 2 giấy tờ trong một trường hợp (không phụ thuộc mã cụ thể)."""
    for q in ["cấp phép nghiên cứu chất ma túy", "đăng ký khai sinh", "đăng ký tạm trú", "cấp lại thẻ căn cước",
              "thu thập thông tin sinh trắc học", "đăng ký kết hôn", "cấp giấy phép"]:
        try:
            d = lay(f"{base}/api/tra-cuu?" + urllib.parse.urlencode({"q": q}))
        except Exception:
            continue
        for it in d.get("items", [])[:8]:
            ct = lay(f"{base}/api/guidelines/{it['id']}")
            hs = (ct.get("data") or {}).get("ThanhPhanHoSo")
            hs = hs if isinstance(hs, list) else ([hs] if isinstance(hs, dict) else [])
            for h in hs:
                gt = h.get("DanhSachGiayTo") if isinstance(h, dict) else None
                gt = gt if isinstance(gt, list) else ([gt] if isinstance(gt, dict) else [])
                if len([g for g in gt if isinstance(g, dict) and (g.get("TenGiayTo") or "").strip()]) >= 2:
                    return ct
    return None


async def _chay(a):
    from playwright.async_api import async_playwright
    base = a.url.rstrip("/")
    ct = tim_thu_tuc_co_ho_so(base)
    print(f"Thủ tục dùng để thử: {ct['procedure_code'] if ct else 'KHÔNG TÌM THẤY'} {ct['title'][:70] if ct else ''}\n")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        loi = []
        ctx = await b.new_context(viewport={"width": 1366, "height": 860})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: loi.append(str(e)))
        pg.on("console", lambda m: loi.append(m.text) if m.type == "error" else None)

        print("A. Trang đầu và tra cứu")
        await pg.goto(base + "/")
        await pg.wait_for_selector("#ags a", timeout=20000)
        thu("A1 trang đầu nạp danh sách cơ quan và câu số liệu",
            await pg.locator("#ags a").count() > 0 and "thủ tục" in await pg.inner_text("#nums"), await pg.inner_text("#nums"))
        await pg.keyboard.press("Tab")
        thu("A2 phím Tab đầu tiên vào “Chuyển đến nội dung chính”",
            await pg.evaluate("document.activeElement.classList.contains('skip-link')"))
        await pg.fill("#q", "đăng ký")
        await pg.focus("#q")
        await pg.keyboard.type(" ")
        try:
            await pg.wait_for_selector("#sug:not(.hidden) div", timeout=5000)
            await pg.keyboard.press("ArrowDown")
            thu("A3 gợi ý khi gõ, chọn được bằng phím mũi tên",
                bool(await pg.get_attribute("#q", "aria-activedescendant")))
        except Exception as e:
            thu("A3 gợi ý khi gõ, chọn được bằng phím mũi tên", False, e)
        await pg.click("#mAsk")
        thu("A4 chuyển sang “Hỏi trợ lý” thì ẩn gợi ý và đổi nhãn ô nhập",
            await pg.eval_on_selector("#sug", "e=>e.classList.contains('hidden')")
            and "câu hỏi" in (await pg.inner_text("#qLabel")).lower(), await pg.inner_text("#qLabel"))
        await pg.click("#mSearch")
        await pg.fill("#q", "dang ky tam tru")
        await pg.click("#go")
        await pg.wait_for_selector(".hit", timeout=20000)
        thu("A5 tra cứu không dấu có kết quả, có nhãn kiểu khớp",
            await pg.locator(".hit").count() > 0 and await pg.locator(".hit .khop").count() > 0, await pg.inner_text("#lMeta"))
        thu("A6 mục điều hướng “Tra cứu” được đánh dấu ở trang kết quả",
            await pg.get_attribute('nav.menu a[data-nav="home"]', "aria-current") == "page")
        # Bổ sung 21/10: lọc theo cấp thực hiện
        await pg.select_option("#fCap", "tinh")
        await pg.wait_for_function("location.hash.includes('cap=tinh')", timeout=10000)
        await pg.wait_for_timeout(1500)
        the = await pg.evaluate("[...document.querySelectorAll('.hit')].map(h=>h.innerText.includes('Cấp tỉnh'))")
        rong = await pg.locator("#hits .empty").count()
        thu("A7 lọc “Cấp thực hiện: Cấp tỉnh”: mọi kết quả đều có nhãn Cấp tỉnh, đường dẫn giữ bộ lọc (bổ sung 21/10)",
            (the and all(the)) or rong == 1, (the[:5], rong))
        await pg.select_option("#fCap", "")

        print("B. Trang chi tiết và phiếu chuẩn bị hồ sơ")
        if not ct:
            thu("B0 tìm được thủ tục có thành phần hồ sơ để thử", False, "kho không có dữ liệu chi tiết")
        else:
            await pg.goto(f"{base}/#/thu-tuc/{ct['id']}")
            await pg.wait_for_selector("input.tick", timeout=20000)
            ten = await pg.eval_on_selector_all("section.blk > h2", "a=>a.map(x=>x.textContent.replace(/^\\s*\\d+\\.\\s*/,'').trim())")

            def vt(t):
                return next((i for i, x in enumerate(ten) if x.startswith(t)), None)
            thu_tu = [vt("Trình tự"), vt("Cách thức"), vt("Thành phần hồ sơ")]
            ok = all(x is not None for x in thu_tu) and thu_tu == sorted(thu_tu)
            if vt("Yêu cầu") is not None and vt("Phí") is not None:
                ok = ok and vt("Yêu cầu") < vt("Phí")
            thu("B1 các mục theo thứ tự Điều 8 NĐ 63/2010 (trình tự, cách thức, hồ sơ, …, điều kiện, phí)", ok, ten)
            await pg.check("#tk-0-0")
            await pg.check("#tk-0-1")
            await pg.reload()
            await pg.wait_for_selector("input.tick")
            thu("B2 dấu tích còn sau khi tải lại trang",
                await pg.is_checked("#tk-0-0") and await pg.is_checked("#tk-0-1"))
            gia_tri = await pg.evaluate(f"localStorage.getItem('phieu-ho-so:{ct['id']}')") or ""
            thu("B3 bộ nhớ trình duyệt chỉ lưu mã băm ngắn, không lưu cả danh sách giấy tờ", 0 < len(gia_tri) < 300, len(gia_tri))
            n = await pg.locator('input.tick[data-c="0"]').count()
            for i in range(n):
                await pg.check(f"#tk-0-{i}")
            thu("B4 đánh dấu đủ một trường hợp: hiện dòng “đã đánh dấu”, không có con dấu giả",
                await pg.locator(".case.du .self-check-complete").first.is_visible()
                and await pg.locator(".dau-moc").count() == 0)
            await pg.click("#xoaDau")
            thu("B5 “Bỏ mọi dấu tích” xóa hết dấu",
                await pg.eval_on_selector_all("input.tick", "a=>a.filter(x=>x.checked).length") == 0)
            await pg.emulate_media(media="print")
            thu("B6 bản in ẩn phiếu và thanh điều hướng, hiện dòng nguồn",
                await pg.eval_on_selector("aside.phieu", "e=>getComputedStyle(e).display") == "none"
                and await pg.eval_on_selector(".chi-in", "e=>getComputedStyle(e).display") == "block")
            await pg.emulate_media(media="screen")
            await pg.click("#mRaw")
            thu("B7 chế độ “Nguyên bản API” có phần dữ liệu gốc JSON",
                "Dữ liệu gốc (JSON)" in await pg.inner_text("#vDetail"))
            fonts = await pg.evaluate("document.fonts.ready.then(()=>[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family))")
            thu("B8 phông tự lưu được nạp (Be Vietnam Pro, Source Serif 4), không cần mạng",
                any("Be Vietnam Pro" in f for f in fonts) and any("Source Serif 4" in f for f in fonts), sorted(set(fonts)))
            # Bổ sung 15/10: một chú thích CSS hỏng từng làm trình duyệt bỏ qua một khai báo phông
            # mà B8 không phát hiện, nên so số khai báo trình duyệt nhận với số khai báo trong tệp.
            ff = await pg.evaluate("""(async()=>{const s=[...document.styleSheets].find(x=>(x.href||'').includes('fonts.css'));
                const txt=await (await fetch(s.href)).text();
                return [[...s.cssRules].filter(r=>r instanceof CSSFontFaceRule).length,(txt.match(/@font-face/g)||[]).length];})()""")
            thu("B9 trình duyệt nhận đủ mọi khai báo @font-face trong fonts.css (bổ sung 15/10)", ff[0] == ff[1] > 0, ff)

        print("C. Trợ lý")
        await pg.goto(base + "/#/tro-ly")
        await pg.wait_for_selector("#starters button")
        cau = (ct["title"] if ct else "đăng ký khai sinh") + " cần giấy tờ gì"
        await pg.fill("#cq", cau)
        await pg.press("#cq", "Enter")
        await pg.wait_for_selector(".a:not(.cho)", timeout=30000)
        thu("C1 câu trả lời có khung “thủ tục được dùng để trả lời” và dòng nguồn",
            await pg.locator(".answer-procedure").count() > 0 and await pg.locator(".a .src").count() > 0)
        await pg.fill("#cq", "còn lệ phí thì sao")
        await pg.press("#cq", "Enter")
        await pg.wait_for_function("document.querySelectorAll('.a:not(.cho)').length>=2", timeout=30000)
        thu("C2 hỏi tiếp hiểu là hỏi về thủ tục ở câu trước",
            "câu trước" in (await pg.locator(".a").last.inner_text()).lower() or await pg.locator(".a").last.locator(".answer-procedure").count() > 0)
        await pg.fill("#cq", "cách nấu phở bò")
        await pg.press("#cq", "Enter")
        await pg.wait_for_function("document.querySelectorAll('.a:not(.cho)').length>=3", timeout=30000)
        thu("C3 câu ngoài phạm vi bị từ chối", await pg.locator(".a").last.evaluate("e=>e.classList.contains('refuse')"))
        o_nhap = """(()=>{const c=document.querySelector('.composer').getBoundingClientRect();
            return [Math.round(c.bottom),innerHeight,document.documentElement.scrollHeight];})()"""
        vt = await pg.evaluate(o_nhap)
        thu("C5 ba lượt hỏi đáp: ô nhập vẫn nằm trong màn hình, trang không cuộn dọc (bổ sung 15/10)",
            vt[0] <= vt[1] and vt[2] <= vt[1] + 1, vt)
        await pg.click("#chatNew")
        thu("C4 “Bắt đầu cuộc hỏi mới” xóa hội thoại", await pg.locator("#msgs > div").count() == 0)

        if a.tk and a.mk:
            print("D. Khu vực cán bộ")
            await pg.goto(base + "/quan_tri.html")
            await pg.fill("#lu", a.tk)
            await pg.fill("#lp", a.mk)
            await pg.click("#login button")
            await pg.wait_for_selector("#drows tr", timeout=20000)
            thu("D1 đăng nhập, thấy danh sách hướng dẫn", await pg.locator("#drows tr").count() > 0)
            await pg.click('[data-tab="logs"]')
            await pg.wait_for_selector("#lk .kpi", timeout=20000)
            thu("D2 thẻ nhật ký: đổi trạng thái chọn của thẻ và hiện số liệu",
                await pg.get_attribute('[data-tab="logs"]', "aria-selected") == "true")
            # Bổ sung 20/10 bản 3 (báo cáo kiểm thử độc lập F22): phím mũi tên, Home trên các thẻ
            await pg.focus('[data-tab="logs"]')
            await pg.keyboard.press("ArrowRight")
            sau_phai = await pg.get_attribute('[data-tab="kho"]', "aria-selected")
            await pg.keyboard.press("Home")
            sau_home = await pg.get_attribute('[data-tab="docs"]', "aria-selected")
            tab_idx = await pg.evaluate("[...document.querySelectorAll('.tabs button')].map(b=>b.tabIndex)")
            thu("D3 thẻ cán bộ: mũi tên phải, Home chuyển thẻ; chỉ thẻ đang chọn nằm trong thứ tự Tab (bổ sung 20/10)",
                sau_phai == "true" and sau_home == "true" and tab_idx[0] == 0 and set(tab_idx[1:]) == {-1}, (sau_phai, sau_home, tab_idx))
            await pg.click('[data-tab="docs"]')
            await pg.wait_for_selector("#drows tr", timeout=20000)

            # F02, F15: mọi yêu cầu sửa/lưu dưới đây bị CHẶN trong trình duyệt và trả lời giả,
            # không có gì được ghi vào database.
            gui = []

            async def gia_lap(route):
                rq = route.request
                duoi = rq.url.split("/api/quan-tri/thu-tuc")[-1]
                if rq.method == "GET" and duoi in ("/900000001", "/900000002"):
                    ten = "Alpha" if duoi.endswith("1") else "Beta"
                    if ten == "Alpha":
                        await asyncio.sleep(0.7)
                    await route.fulfill(status=200, content_type="application/json", body=json.dumps(
                        {"id": int(duoi[1:]), "title": f"Hướng dẫn {ten}", "agency": ten, "category": ten,
                         "status": "draft", "data": {"NoiDungHuongDan": f"Nội dung {ten}"}}, ensure_ascii=False))
                elif rq.method in ("PUT", "POST"):
                    gui.append((rq.method, duoi, rq.post_data))
                    await asyncio.sleep(0.7)
                    await route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
                else:
                    await route.continue_()

            await pg.route(CHAN_THU_TUC, gia_lap)
            await pg.evaluate("openForm(900000001); setTimeout(()=>openForm(900000002), 50)")
            await pg.wait_for_timeout(1500)
            o = await pg.evaluate("[$('f1').value,$('f4').value,EDIT]")
            await pg.click("#form button[type=submit]")
            await pg.wait_for_timeout(1200)
            thu("D4 mở sửa A (mạng chậm) rồi B: form hiện và lưu đúng bản B, nội dung A không ghi vào B (bổ sung 20/10)",
                o == ["Hướng dẫn Beta", "Nội dung Beta", 900000002] and len(gui) == 1 and gui[0][1] == "/900000002"
                and "Beta" in (gui[0][2] or "") and "Alpha" not in (gui[0][2] or ""), (o, gui))
            await pg.evaluate("openForm(900000001); setTimeout(()=>closeForm(), 50)")
            await pg.wait_for_timeout(1200)
            thu("D5 đóng form khi đang tải: form không tự mở lại (bổ sung 20/10)",
                await pg.evaluate("$('modal').classList.contains('hidden')"))
            gui.clear()
            await pg.evaluate("openForm(null)")
            await pg.fill("#f1", "Thử lưu hai lần")
            await pg.fill("#f4", "Nội dung thử, không được ghi vào database")
            await pg.evaluate("$('form').requestSubmit(); $('form').requestSubmit()")
            await pg.press("#f1", "Enter")
            dang_luu = await pg.evaluate("(b=>[b.disabled,b.textContent])(document.querySelector('#form button[type=submit]'))")
            await pg.wait_for_timeout(1500)
            thu("D6 nhấn Lưu nhiều lần liên tiếp chỉ gửi MỘT yêu cầu; nút báo “Đang lưu…” (bổ sung 20/10)",
                len([x for x in gui if x[0] == "POST"]) == 1 and dang_luu == [True, "Đang lưu…"], (gui, dang_luu))
            # Bổ sung 21/10 bản 2 (N02): lưu A trên mạng chậm, bấm Hủy, mở form mới và gõ; phản hồi
            # của A không được đóng hay xóa form mới.
            gui.clear()
            await pg.evaluate("openForm(null)")
            await pg.fill("#f1", "Bản Alpha đang lưu")
            await pg.fill("#f4", "Nội dung Alpha đủ dài để lưu thử")
            await pg.evaluate("$('form').requestSubmit()")
            await pg.wait_for_timeout(150)
            await pg.evaluate("closeForm()")
            await pg.evaluate("openForm(null)")
            await pg.fill("#f1", "Bản Gamma đang soạn")
            await pg.wait_for_timeout(1200)
            gamma = await pg.evaluate("[!$('modal').classList.contains('hidden'), $('f1').value, $('ferr').textContent]")
            thu("D10 phản hồi lưu của bản cũ không đóng hay xóa form mới đang soạn (bổ sung 21/10 bản 2)",
                gamma[0] and gamma[1] == "Bản Gamma đang soạn" and len(gui) == 1, (gamma, gui))
            await pg.evaluate("closeForm()")
            await pg.unroute(CHAN_THU_TUC)
            chan_het = all(x[1] in ("", "/900000001", "/900000002") for x in gui)
            thu("D0 mọi yêu cầu ghi trong D4–D10 đều bị chặn trong trình duyệt, không tới máy chủ (bổ sung 21/10 bản 2)",
                chan_het, gui)
            # Bổ sung 21/10: xem trước, cảnh báo thay đổi chưa lưu, lịch sử thao tác (không ghi gì vào database)
            await pg.evaluate("openForm(null)")
            await pg.fill("#f1", "Hướng dẫn xem thử")
            await pg.fill("#f4", "Dòng một\nDòng hai <b>không phải thẻ</b>")
            await pg.click("#fprev")
            xt = await pg.inner_text("#fpre")
            thu("D7 “Xem trước như người dân” hiện tên, nhãn cán bộ biên soạn và nội dung (không chạy thẻ HTML) (bổ sung 21/10)",
                "Hướng dẫn xem thử" in xt and "cán bộ biên soạn" in xt and "<b>không phải thẻ</b>" in xt, xt[:160])
            await pg.fill("#f1", "Tên đã sửa sau khi mở xem trước")
            xt2 = await pg.inner_text("#fpre")
            thu("D11 sửa nội dung khi đang xem trước: bản xem trước cập nhật ngay (bổ sung 21/10 bản 2)",
                "Tên đã sửa sau khi mở xem trước" in xt2 and "Hướng dẫn xem thử" not in xt2, xt2[:120])
            hop = []

            async def tra_loi_hop(dlg):
                hop.append(dlg.message)
                await (dlg.dismiss() if len(hop) == 1 else dlg.accept())

            pg.on("dialog", tra_loi_hop)
            await pg.click("#fcancel")
            con_mo = not await pg.evaluate("$('modal').classList.contains('hidden')")
            await pg.click("#fcancel")
            da_dong = await pg.evaluate("$('modal').classList.contains('hidden')")
            pg.remove_listener("dialog", tra_loi_hop)
            thu("D8 đóng form còn thay đổi chưa lưu: hỏi xác nhận; chọn ở lại thì form vẫn mở (bổ sung 21/10)",
                len(hop) == 2 and "chưa lưu" in hop[0] and con_mo and da_dong, (hop, con_mo, da_dong))
            await pg.click('[data-tab="thaotac"]')
            await pg.wait_for_selector("#trows tr", timeout=20000)
            bang = await pg.inner_text("#trows")
            thu("D9 thẻ “Lịch sử thao tác” ghi lần đăng nhập vừa rồi kèm tên cán bộ (bổ sung 21/10)",
                "Đăng nhập" in bang and a.tk in bang, bang[:160])
            await pg.click('[data-tab="docs"]')
            await pg.click("#out")

        # Bổ sung 20/10 bản 3 (F20): trang riêng, không tính lỗi tải tài nguyên 429 cố ý vào Z1
        g = await ctx.new_page()

        async def tra_429(route):
            await route.fulfill(status=429, content_type="application/json", headers={"Retry-After": "60"},
                                body='{"detail": "quá nhiều"}')

        await g.route("**/api/tra-cuu**", tra_429)
        await g.goto(base + "/#/tim?q=" + urllib.parse.quote("đăng ký khai sinh"))
        await g.wait_for_selector("#hits .empty", timeout=20000)
        chu = await g.inner_text("#hits")
        thu("F1 bị giới hạn lượt (429): báo chờ một phút, không báo nhầm là mất kết nối máy chủ (bổ sung 20/10)",
            "quá nhiều yêu cầu" in chu and "Không kết nối được" not in chu, chu[:160])
        await g.close()

        print("E. Điện thoại (320 và 390 px): không tràn ngang")
        for rong in (320, 390):
            m = await b.new_page(viewport={"width": rong, "height": 800})
            m.on("pageerror", lambda e: loi.append(str(e)))
            trang = ["/", "/#/tim?q=" + urllib.parse.quote("đăng ký tạm trú"), "/#/tro-ly", "/quan_tri.html"]
            if ct:
                trang.append(f"/#/thu-tuc/{ct['id']}")
            tran = []
            for t in trang:
                await m.goto(base + t)
                await m.wait_for_timeout(1500)
                if await m.evaluate("document.documentElement.scrollWidth>innerWidth"):
                    tran.append(t)
            thu(f"E{1 if rong == 320 else 2} bề rộng {rong} px: không trang nào tràn ngang", not tran, tran)
            nho = await m.evaluate("""(()=>{let min=99;document.querySelectorAll('body *').forEach(e=>{
                if(e.offsetParent&&e.childNodes.length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))
                  min=Math.min(min,parseFloat(getComputedStyle(e).fontSize));});return min;})()""")
            thu(f"E{3 if rong == 320 else 4} cỡ chữ nhỏ nhất trên trang cuối cùng ≥ 12,5 px", nho >= 12.5, nho)
            # Bổ sung 15/10: ô nhập của trợ lý phải thấy được ngay, trước và sau khi có câu trả lời
            vi_tri = []
            for cao in (900, 640):
                await m.set_viewport_size({"width": rong, "height": cao})
                await m.goto(base + "/#/tro-ly")
                await m.reload()   # tải lại để bắt đầu từ hội thoại trống
                await m.wait_for_selector("#starters button")
                truoc = await m.evaluate(o_nhap)
                await m.fill("#cq", "đăng ký khai sinh cần giấy tờ gì")
                await m.press("#cq", "Enter")
                await m.wait_for_selector(".a:not(.cho)", timeout=30000)
                sau = await m.evaluate(o_nhap)
                vi_tri.append((cao, truoc, sau))
            thu(f"E{5 if rong == 320 else 6} bề rộng {rong} px, cao 900 và 640: ô nhập của trợ lý nằm trong màn hình, "
                "trang không cuộn dọc (bổ sung 15/10)",
                all(x[0] <= x[1] and x[2] <= x[1] + 1 for _, t, s_ in vi_tri for x in (t, s_)), vi_tri)
            await m.close()

        thu("Z1 không có lỗi JavaScript trong toàn bộ các bước trên", not loi, loi[:3])
        await b.close()
    return _bao_cao(a)


def _bao_cao(a):
    dat = sum(1 for _, d, _ in KQ if d)
    tong = f"\nKẾT QUẢ: {dat}/{len(KQ)} phép thử giao diện đạt"
    print(tong)
    if a.luu:
        with open(a.luu, "w", encoding="utf-8") as f:
            for ten, d, tt in KQ:
                f.write(("ĐẠT   " if d else "TRƯỢT ") + ten + ("" if d else f"  ← {tt}") + "\n")
            f.write(tong + "\n")
    return 0 if dat == len(KQ) else 1


async def main(a):
    """Bộ thử dừng giữa chừng vẫn ghi báo cáo, kèm lý do dừng (bổ sung 21/10 bản 2)."""
    try:
        return await _chay(a)
    except Exception as e:
        thu("Z0 bộ thử dừng giữa chừng", False, f"{type(e).__name__}: {e}")
        _bao_cao(a)
        return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--tk", help="tài khoản cán bộ (QUAN_TRI_TAI_KHOAN)")
    ap.add_argument("--mk", help="mật khẩu cán bộ (QUAN_TRI_MAT_KHAU)")
    ap.add_argument("--luu", help="ghi kết quả ra tệp")
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Chưa cài Playwright. Chạy:  pip install playwright  rồi  python -m playwright install chromium")
        sys.exit(2)
    sys.exit(asyncio.run(main(ap.parse_args())))
