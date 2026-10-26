"""Adversarial probes of claimed guarantees; no production code changes."""
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'backend'))
from app.tro_ly import kiem_tra_loi_dan
from doi_chieu_nguon import doi_chieu
rows=[]
for text in ['Hồ sơ yêu cầu hộ chiếu.','Nộp hồ sơ tại Đại sứ quán.','Ho so khong can giay to.','The processing time is three days.']:
    r=kiem_tra_loi_dan(text,'Đăng ký khai sinh');rows.append({'kind':'intro','input':text,'check':r,'unsupported_intro_accepted':r['dat']})
data={'CachThucThucHien':[{'HinhThucNop':'DIRECT','ThoiGianXuLy':'3','DonViThoiGian':'WORKING_DAY','DanhSachPhi':[{'TenPhi':'Phí mẫu','SoTien':'125000','MaTienTe':'VND'}]}],
      'ThanhPhanHoSo':{'DanhSachGiayTo':[{'TenGiayTo':'Tờ khai mẫu','SoBanChinh':'1','SoBanSao':'2'}]}}
for y,lines in [('thoi_han',['- Trực tiếp: 3 tháng']),('le_phi',['- Phí mẫu: 125.000 USD [Trực tiếp — 3 tháng]']),('ho_so',['- Tờ khai mẫu (99 bản chính; 88 bản sao)'])]:
    r=doi_chieu(data,y,lines);rows.append({'kind':'source_check','intent':y,'answer':lines,'check':r,'wrong_fact_not_detected':r['co_trong_tra_loi']==r['so_du_kien'] and not r['dong_khong_can_cu']})
(Path(__file__).resolve().parent/'gioi_han_chay_lai.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False,indent=2))
