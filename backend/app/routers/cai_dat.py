"""Trung tâm cấu hình hệ thống — REGISTRY cài đặt (Đợt nâng cấp 2, mục 3/10/11).

Mọi khóa cài đặt được khai báo tập trung trong DANG_KY_CAI_DAT: {khoa, nhom,
nhan (tiếng Việt), mo_ta, kieu (bool|so|text|textarea|select|mau|gio),
mac_dinh, lua_chon (cho select), min/max (cho so/gio)}.

- Giá trị lưu trong bảng system_settings (JSON), đọc RUNTIME mỗi lần xử lý —
  thay đổi có hiệu lực ngay ở request tiếp theo, không cần khởi động lại.
- GET /api/cai-dat           -> dict {khoa: gia_tri} (tương thích ngược).
- GET /api/cai-dat/dang-ky   -> registry đầy đủ + giá trị hiện tại (UI tự sinh control).
- PUT /api/cai-dat           -> lưu các khóa hợp lệ trong registry (kèm kiểm tra kiểu/ràng buộc).
- POST /api/cai-dat/khoi-phuc-mac-dinh {nhom?} -> xóa giá trị đã lưu của nhóm (hoặc tất cả).

Bí mật (khóa API, connector secret) KHÔNG nằm trong registry này.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SystemSetting, User
from ..deps import get_current_user, require_admin
from ..services.ai_gateway import PROMPT_TRO_CHUYEN_TU_DO_MAC_DINH

router = APIRouter(prefix="/api/cai-dat", tags=["Cài đặt hệ thống"])

NHOM_CAI_DAT = {
    "hanh_vi_bot": {"ten": "Hành vi bot", "icon": "fa-solid fa-robot",
                    "mo_ta": "Cách bot vận hành: giờ hoạt động, từ khóa cấm, tin nhắn chào/ngoài giờ, ngưỡng chuyển nhân viên."},
    "phong_cach": {"ten": "Phong cách trả lời", "icon": "fa-solid fa-wand-magic-sparkles",
                   "mo_ta": "Danh tính, xưng hô, giọng điệu và độ sáng tạo của câu trả lời AI (chống trả lời một motip)."},
    "tro_chuyen": {"ten": "Chế độ trò chuyện tự do", "icon": "fa-solid fa-face-laugh-wink",
                   "mo_ta": "Bật lên là bot NGHỈ BÁN HÀNG, chuyển sang nói chuyện như bạn bè bình thường: ai nhắn gì rep nấy, giải trí, cà khịa. Khi bật: không chèn tri thức/doanh nghiệp, không hỏi số điện thoại, không báo lead cho admin."},
    "doanh_nghiep": {"ten": "Thông tin doanh nghiệp", "icon": "fa-solid fa-building",
                     "mo_ta": "Thông tin doanh nghiệp được đưa vào ngữ cảnh AI để trả lời khách chính xác."},
    "thu_thap": {"ten": "Thu thập thông tin", "icon": "fa-solid fa-clipboard-list",
                 "mo_ta": "Bot tự bóc tách thông tin khách (SĐT, nhu cầu...) và hỏi bổ sung khi thiếu."},
    "thong_bao": {"ten": "Thông báo admin", "icon": "fa-solid fa-bell",
                  "mo_ta": "Sự kiện nào được báo cho quản trị viên, kênh báo và tần suất chống spam."},
    "nhom_gui_tin": {"ten": "Zalo nhóm & gửi tin", "icon": "fa-solid fa-comments",
                     "mo_ta": "Thả tim, chia nhỏ tin nhắn, hiệu ứng đang soạn tin và hành vi của bot trong nhóm Zalo."},
    "he_thong": {"ten": "Hệ thống & module", "icon": "fa-solid fa-gear",
                 "mo_ta": "Múi giờ, màu chủ đạo và công tắc bật/tắt các module lớn."},
}

def _k(khoa, nhom, nhan, mo_ta, kieu, mac_dinh, **kw):
    d = {"khoa": khoa, "nhom": nhom, "nhan": nhan, "mo_ta": mo_ta, "kieu": kieu, "mac_dinh": mac_dinh}
    d.update(kw)
    return d

DANG_KY_CAI_DAT = [
    # ---- Nhóm: Hành vi bot ----
    _k("tu_dong_tra_loi_toan_cuc", "hanh_vi_bot", "Tự động trả lời toàn cục",
       "Tắt = bot không tự trả lời ở mọi hội thoại (vẫn nhận và lưu tin). Vẫn bật/tắt riêng được từng hội thoại.", "bool", True),
    _k("che_do_duyet_truoc_khi_gui", "hanh_vi_bot", "Chế độ duyệt trước khi gửi",
       "Bot chỉ soạn câu trả lời, nhân viên duyệt mới gửi đi.", "bool", False),
    _k("thoi_gian_gom_tin_ms", "hanh_vi_bot", "Thời gian gom tin nhắn (mili-giây)",
       "Chờ gom nhiều tin liên tiếp của khách thành một ngữ cảnh trước khi trả lời.", "so", 1500, min=0, max=30000),
    _k("gio_hoat_dong_bat_dau", "hanh_vi_bot", "Giờ bắt đầu hoạt động",
       "Bot chỉ tự trả lời trong khung giờ này (theo múi giờ hệ thống). Bắt đầu = kết thúc nghĩa là hoạt động cả ngày.", "gio", 0, min=0, max=24),
    _k("gio_hoat_dong_ket_thuc", "hanh_vi_bot", "Giờ kết thúc hoạt động",
       "Ngoài khung giờ, bot gửi câu trả lời ngoài giờ (nếu đã cấu hình) hoặc im lặng.", "gio", 24, min=0, max=24),
    _k("cau_tra_loi_ngoai_gio", "hanh_vi_bot", "Câu trả lời ngoài giờ",
       "Tin nhắn bot gửi khi khách nhắn ngoài giờ hoạt động. Để trống = im lặng ngoài giờ.", "textarea", ""),
    _k("tu_khoa_cam", "hanh_vi_bot", "Từ khóa cấm (mỗi dòng hoặc phân cách bằng dấu phẩy)",
       "Tin khách chứa từ khóa này thì bot không tự trả lời, chỉ ghi nhật ký để nhân viên xử lý.", "textarea", ""),
    _k("so_lan_yeu_cau_gap_nhan_vien_de_chuyen", "hanh_vi_bot", "Số lần yêu cầu gặp nhân viên thì chuyển thật",
       "Khách yêu cầu gặp nhân viên đủ số lần này trong một hội thoại thì bot chuyển cho nhân viên. 1 = chuyển ngay lần đầu.", "so", 1, min=1, max=10),
    _k("tin_chao_khach_moi", "hanh_vi_bot", "Tin nhắn chào khách mới",
       "Câu chào được nối vào đầu câu trả lời đầu tiên cho khách nhắn lần đầu. Để trống = không chào riêng.", "textarea", ""),
    _k("bot_chu_dong_pr", "hanh_vi_bot", "Bot chủ động giới thiệu dịch vụ (PR)",
       "Bật: danh sách dịch vụ đang mở bán được đưa vào prompt để bot chủ động giới thiệu ngắn gọn khi khách chưa rõ nhu cầu, thay vì hỏi trống. Tắt: bot chỉ tư vấn khi khách hỏi tới.", "bool", True),
    _k("so_dich_vu_pr", "hanh_vi_bot", "Số dịch vụ đưa vào ngữ cảnh PR",
       "Tối đa bao nhiêu dịch vụ đang mở bán được đưa vào prompt mỗi lượt trả lời.", "so", 5, min=1, max=20),
    _k("cau_khi_bot_khong_tra_loi", "hanh_vi_bot", "Tin nhắn khi bot không trả lời được",
       "Khi nhà cung cấp AI lỗi, bot gửi câu này cho khách thay vì im lặng. Để trống = im lặng và báo admin (hành vi hiện tại).", "textarea", ""),
    # ---- Nhóm: Phong cách trả lời (mục 10 — chống một motip) ----
    _k("bot_ten_hien_thi", "phong_cach", "Tên riêng của bot",
       "Tên bot tự xưng trong câu trả lời (ví dụ: Em là An). Để trống = dùng tên hiển thị bên dưới.", "text", ""),
    _k("ten_hien_thi_bot", "phong_cach", "Tên hiển thị của bot",
       "Danh tính bot được khóa trong lời nhắc hệ thống — mô hình không tự giới thiệu sai danh tính.", "text", "Trợ lý hỗ trợ khách hàng"),
    _k("bot_cach_xung_ho", "phong_cach", "Cách xưng hô",
       "Cặp xưng hô bot dùng khi trò chuyện với khách.", "select", "em/bạn",
       lua_chon=["em/bạn", "em/anh-chị", "tôi/bạn", "mình/bạn", "em/quý khách"]),
    _k("bot_giong_dieu", "phong_cach", "Giọng điệu trả lời",
       "Mỗi giọng điệu là một đoạn hướng dẫn phong cách riêng đưa vào prompt của AI.", "select", "tu_nhien_than_thien",
       lua_chon=["tu_nhien_than_thien", "lich_su_trang_trong", "ngan_gon_thang_than"],
       nhan_lua_chon={"tu_nhien_than_thien": "Tự nhiên, thân thiện", "lich_su_trang_trong": "Lịch sự, trang trọng", "ngan_gon_thang_than": "Ngắn gọn, thẳng thắn"}),
    _k("ai_temperature", "phong_cach", "Độ sáng tạo của AI (temperature)",
       "Càng cao càng đa dạng cách diễn đạt (chống motip), càng thấp càng ổn định. Khoảng 0 – 1.5.", "so", 0.85, min=0, max=1.5),
    _k("ai_do_dai_tra_loi", "phong_cach", "Độ dài trả lời mong muốn",
       "Hướng dẫn độ dài câu trả lời: ngắn gọn / vừa phải / chi tiết.", "select", "vua",
       lua_chon=["ngan", "vua", "chi_tiet"],
       nhan_lua_chon={"ngan": "Ngắn gọn", "vua": "Vừa phải", "chi_tiet": "Chi tiết"}),
    _k("prompt_bo_sung", "phong_cach", "Hướng dẫn bổ sung cho AI",
       "Đoạn hướng dẫn riêng của quản trị viên được thêm vào prompt hệ thống (ví dụ quy tắc riêng của doanh nghiệp).", "textarea", ""),
    _k("prompt_tong_quat", "phong_cach", "Prompt tổng quát (toàn văn phần lõi của bot)",
       "Cơ chế: khi ô này CÓ nội dung, đoạn đó THAY phần lõi mặc định của prompt hệ thống (danh tính bot + xưng hô + hướng dẫn giọng điệu/độ dài + luật chống một motip + khóa danh tính). Các phần dữ liệu động vẫn tự chắp phía sau như cũ: thông tin doanh nghiệp, danh sách dịch vụ PR, hồ sơ khách, ngữ cảnh tri thức/bộ nhớ và Hướng dẫn bổ sung. Khi ĐỂ TRỐNG: dùng phần lõi mặc định của hệ thống như trước. Sửa ở trang 'Prompt tổng quát' để xem trước toàn văn prompt đã ghép. Hiệu lực ngay, không cần khởi động lại.", "textarea", ""),
    _k("so_tin_nhan_ngu_canh", "phong_cach", "Số tin lịch sử truyền cho AI",
       "Số tin gần nhất của hội thoại được truyền làm lịch sử đa lượt để AI nhớ ngữ cảnh, không chào lại/lặp lại.", "so", 10, min=1, max=50),
    # ---- Nhóm: Chế độ trò chuyện tự do ----
    _k("che_do_tro_chuyen_tu_do", "tro_chuyen", "Bật chế độ trò chuyện tự do",
       "BẬT = bot nghỉ tư vấn/bán hàng, chuyển sang chat như bạn bè (giải trí, cà khịa). TẮT = bot tư vấn bán hàng như bình thường. Mặc định tắt.", "bool", False),
    _k("prompt_tro_chuyen_tu_do", "tro_chuyen", "Persona trò chuyện tự do (toàn văn)",
       "Toàn bộ chỉ dẫn tính cách của bot khi ở chế độ tự do — sửa tự do theo ý muốn, bot nghe đúng theo đoạn này.", "textarea",
       PROMPT_TRO_CHUYEN_TU_DO_MAC_DINH),
    _k("nhiet_do_tu_do", "tro_chuyen", "Độ ngẫu hứng khi trò chuyện tự do (temperature)",
       "Dùng thay cho temperature tư vấn khi ở chế độ tự do. Càng cao càng ngẫu hứng/linh hoạt. Khoảng 0 – 2.", "so", 1.1, min=0, max=2),
    # ---- Nhóm: Thông tin doanh nghiệp ----
    _k("doanh_nghiep_ten", "doanh_nghiep", "Tên doanh nghiệp", "Đưa vào ngữ cảnh AI.", "text", ""),
    _k("doanh_nghiep_dia_chi", "doanh_nghiep", "Địa chỉ doanh nghiệp", "Đưa vào ngữ cảnh AI.", "text", ""),
    _k("doanh_nghiep_hotline", "doanh_nghiep", "Hotline", "Đưa vào ngữ cảnh AI.", "text", ""),
    _k("doanh_nghiep_gio_mo_cua", "doanh_nghiep", "Giờ mở cửa", "Ví dụ: 8h00 – 21h00 hằng ngày. Đưa vào ngữ cảnh AI.", "text", ""),
    _k("thong_tin_doanh_nghiep_bo_sung", "doanh_nghiep", "Thông tin bổ sung",
       "Mọi thông tin khác về doanh nghiệp cần AI biết khi trả lời khách.", "textarea", ""),
    # ---- Nhóm: Thu thập thông tin ----
    _k("module_thu_thap_thong_tin", "thu_thap", "Bật module thu thập thông tin",
       "Tắt = bot không tự bóc tách thông tin khách từ hội thoại.", "bool", True),
    _k("thu_thap_tu_hoi_sdt", "thu_thap", "Tự hỏi số điện thoại khi khách chưa có",
       "Khi khách hỏi tư vấn/báo giá mà chưa có SĐT, bot hỏi xin số điện thoại (tối đa 1 lần/hội thoại).", "bool", True),
    _k("thu_thap_cau_hoi_sdt", "thu_thap", "Câu hỏi xin số điện thoại",
       "Câu bot dùng để hỏi xin SĐT (với nhà cung cấp thật, AI được gợi ý hỏi tự nhiên theo câu này).", "textarea",
       "Anh/chị cho em xin số điện thoại để tư vấn viên liên hệ tư vấn chi tiết hơn ạ."),
    _k("thu_thap_intent_hoi_sdt", "thu_thap", "Ý định (intent) kích hoạt hỏi SĐT",
       "Danh sách intent phân cách bằng dấu phẩy, ví dụ: hoi_gia. Để trống = mọi intent.", "text", "hoi_gia"),
    _k("thu_thap_tu_khoa_hoi_sdt", "thu_thap", "Từ khóa kích hoạt hỏi SĐT",
       "Từ khóa (không dấu, phân cách dấu phẩy) xuất hiện trong tin khách thì bot hỏi SĐT.", "text", "tu van,bao gia"),
    _k("cac_truong_bat_buoc_thu_thap", "thu_thap", "Trường bắt buộc để coi là đủ thông tin",
       "Danh sách trường phân cách dấu phẩy: so_dien_thoai, ho_ten, email, nhu_cau, dich_vu_quan_tam, ngan_sach, thoi_gian_mong_muon, dia_chi.", "text", "so_dien_thoai,nhu_cau"),
    # ---- Nhóm: Thông báo admin ----
    _k("thong_bao_admin_zalo_thread_id", "thong_bao", "ID hội thoại Zalo của admin",
       "Thread Zalo cá nhân để bot gửi thông báo cho admin. Để trống = chỉ hiện trong Trung tâm thông báo.", "text", ""),
    _k("thong_bao_khach_moi", "thong_bao", "Báo khi có khách mới", "", "bool", True),
    _k("thong_bao_co_so_dien_thoai", "thong_bao", "Báo khi khách để lại số điện thoại", "", "bool", True),
    _k("thong_bao_du_thong_tin", "thong_bao", "Báo khi đã thu thập đủ thông tin khách", "", "bool", True),
    _k("thong_bao_gap_nhan_vien", "thong_bao", "Báo khi khách yêu cầu gặp nhân viên", "", "bool", True),
    _k("thong_bao_khieu_nai", "thong_bao", "Báo khi khách có dấu hiệu khiếu nại", "", "bool", True),
    _k("thong_bao_bot_khong_tra_loi_duoc", "thong_bao", "Báo khi bot không trả lời được (lỗi AI)", "", "bool", True),
    _k("thong_bao_loi_he_thong", "thong_bao", "Báo khi có lỗi hệ thống / lỗi gửi tin", "", "bool", True),
    _k("thong_bao_cua_so_chong_trung_phut", "thong_bao", "Cửa sổ chống trùng thông báo (phút)",
       "Cùng loại + cùng khách trong khoảng này chỉ tạo 1 thông báo (trừ yêu cầu gặp nhân viên).", "so", 10, min=1, max=1440),
    _k("thong_bao_gian_cach_gui_zalo_giay", "thong_bao", "Giãn cách gửi thông báo qua Zalo (giây)",
       "Tối thiểu bao nhiêu giây giữa hai lần gửi thông báo Zalo cho admin, chống spam.", "so", 60, min=0, max=3600),
    # ---- Nhóm: Zalo nhóm & gửi tin ----
    _k("bot_tha_tim", "nhom_gui_tin", "Bot thả tim tin nhắn của khách",
       "Khi bật, bot thả reaction ❤ vào tin khách trước khi trả lời (qua zca-js addReaction). Mặc định tắt.", "bool", False),
    _k("gui_tin_chia_nho", "nhom_gui_tin", "Gửi tin chia nhỏ như người thật",
       "Câu trả lời dài được tách thành nhiều tin liên tiếp theo đoạn/câu thay vì gửi một cục.", "bool", True),
    _k("do_dai_toi_da_moi_tin", "nhom_gui_tin", "Độ dài tối đa mỗi tin (ký tự)",
       "Mỗi phần tin sau khi chia không vượt quá số ký tự này.", "so", 350, min=80, max=2000),
    _k("do_tre_giua_cac_tin_ms", "nhom_gui_tin", "Độ trễ giữa các tin (mili-giây)",
       "Nghỉ ngắn giữa hai tin liên tiếp để giống người thật gõ.", "so", 700, min=0, max=5000),
    _k("hieu_ung_dang_soan_tin", "nhom_gui_tin", "Hiệu ứng 'đang soạn tin'",
       "Gửi sự kiện đang soạn tin (zca-js sendTypingEvent) trước mỗi phần tin.", "bool", False),
    _k("bot_nhom_chi_khi_duoc_tag", "nhom_gui_tin", "Trong nhóm chỉ trả lời khi được tag đích danh",
       "Bật: bot chỉ trả lời khi mention chứa đúng UID tài khoản bot hoặc tên bot. Tag @all KHÔNG tính. Tắt: trả lời mọi tin nhóm.", "bool", True),
    _k("ten_bot_trong_nhom", "nhom_gui_tin", "Tên bot trong nhóm",
       "Tên hiển thị của bot trong nhóm — tin nhóm chứa tên này cũng được coi là gọi bot. Để trống = chỉ tính mention UID.", "text", ""),
    _k("danh_sach_nhom_duoc_phep", "nhom_gui_tin", "Danh sách nhóm được phép (ID nhóm, phân cách dấu phẩy)",
       "Để trống = mọi nhóm (vẫn phải tag đúng). Có danh sách = chỉ các nhóm này bot mới hoạt động.", "textarea", ""),
    # ---- Nhóm: Hệ thống & module ----
    _k("bo_nho_tom_tat_sau_bao_nhieu_tin", "he_thong", "Tóm tắt hồ sơ khách sau mỗi (tin nhắn của khách)",
       "Sau mỗi bấy nhiêu tin nhắn mới của khách, bot tự tóm tắt gộp thành hồ sơ dài hạn (bot nhớ về khách) và dùng trong các lượt trả lời sau.", "so", 6, min=1, max=100),
    _k("mui_gio", "he_thong", "Múi giờ hệ thống", "Mặc định Asia/Ho_Chi_Minh.", "select", "Asia/Ho_Chi_Minh",
       lua_chon=["Asia/Ho_Chi_Minh", "Asia/Bangkok", "Asia/Singapore", "Asia/Tokyo", "UTC"]),
    _k("mau_chu_dao_giao_dien", "he_thong", "Màu chủ đạo giao diện",
       "Màu thương hiệu dùng cho điểm nhấn trong giao diện quản trị.", "mau", "#0068ff"),
    _k("module_tu_dong_hoa", "he_thong", "Module Quy tắc tự động hóa",
       "Tắt = bỏ qua toàn bộ quy tắc tự động hóa khi xử lý tin nhắn.", "bool", True),
    _k("module_bo_nho_ai", "he_thong", "Module Bộ nhớ AI",
       "Tắt = không truy xuất/ghi bộ nhớ dài hạn khi trả lời.", "bool", True),
    _k("module_thong_bao_admin", "he_thong", "Module Thông báo admin",
       "Tắt = không tạo thông báo admin cho mọi sự kiện.", "bool", True),
    _k("module_gui_thong_bao_zalo_admin", "he_thong", "Gửi thông báo qua Zalo cho admin",
       "Tắt = thông báo chỉ nằm trong Trung tâm thông báo, không gửi qua Zalo.", "bool", True),
    # ---- Đợt nâng cấp 3, mục 3: Vector DB / tìm kiếm ngữ nghĩa ----
    _k("tim_kiem_ngu_nghia", "he_thong", "Tìm kiếm ngữ nghĩa (Vector DB)",
       "Bật: truy xuất kho tri thức và bộ nhớ hợp nhất điểm ngữ nghĩa (cosine trên vector nhúng) với điểm từ khóa. Muốn có kết quả ngữ nghĩa phải có vector đã nhúng (Kho tri thức → nút Nhúng lại toàn bộ) và nguồn embedding sẵn sàng. Tắt hoặc chưa có vector: hệ thống tự dùng tìm từ khóa như cũ.", "bool", True),
    _k("so_ket_qua_ngu_nghia", "he_thong", "Số kết quả ngữ nghĩa tối đa",
       "Số đoạn tri thức/ký ức lấy theo độ tương đồng ngữ nghĩa trong mỗi lần truy hồi (hợp nhất với kết quả từ khóa).", "so", 4, min=1, max=20),
]

MAC_DINH = {d["khoa"]: d["mac_dinh"] for d in DANG_KY_CAI_DAT}
_THEO_KHOA = {d["khoa"]: d for d in DANG_KY_CAI_DAT}


class CaiDatIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    tu_dong_tra_loi_toan_cuc: Optional[bool] = None
    thoi_gian_gom_tin_ms: Optional[int] = None
    che_do_duyet_truoc_khi_gui: Optional[bool] = None
    mui_gio: Optional[str] = None
    so_tin_nhan_ngu_canh: Optional[int] = None
    ten_hien_thi_bot: Optional[str] = None
    thong_bao_admin_zalo_thread_id: Optional[str] = None
    thong_bao_khach_moi: Optional[bool] = None
    thong_bao_co_so_dien_thoai: Optional[bool] = None
    thong_bao_du_thong_tin: Optional[bool] = None
    thong_bao_gap_nhan_vien: Optional[bool] = None
    thong_bao_khieu_nai: Optional[bool] = None
    thong_bao_bot_khong_tra_loi_duoc: Optional[bool] = None
    thong_bao_loi_he_thong: Optional[bool] = None


def doc_cai_dat(db: Session) -> dict:
    """Đọc toàn bộ cài đặt: giá trị đã lưu trong DB ghi đè mặc định của registry."""
    ket_qua = dict(MAC_DINH)
    for dong in db.query(SystemSetting).all():
        try:
            ket_qua[dong.key] = json.loads(dong.value)
        except Exception:
            ket_qua[dong.key] = dong.value
    return ket_qua


def _kiem_tra_gia_tri(dinh_nghia: dict, gia_tri):
    """Ép kiểu + kiểm tra ràng buộc theo registry. Ném HTTPException 400 nếu sai."""
    kieu = dinh_nghia["kieu"]; khoa = dinh_nghia["khoa"]
    if kieu == "bool":
        if not isinstance(gia_tri, bool):
            raise HTTPException(400, f"Cài đặt {khoa} phải là đúng/sai (boolean)")
        return gia_tri
    if kieu in ("so", "gio"):
        try:
            so = float(gia_tri)
        except (TypeError, ValueError):
            raise HTTPException(400, f"Cài đặt {khoa} phải là số")
        if "min" in dinh_nghia and so < dinh_nghia["min"]:
            raise HTTPException(400, f"Cài đặt {khoa} phải >= {dinh_nghia['min']}")
        if "max" in dinh_nghia and so > dinh_nghia["max"]:
            raise HTTPException(400, f"Cài đặt {khoa} phải <= {dinh_nghia['max']}")
        return int(so) if float(so).is_integer() else so
    if kieu == "select":
        if gia_tri not in dinh_nghia.get("lua_chon", []):
            raise HTTPException(400, f"Giá trị không hợp lệ cho {khoa}: {gia_tri}")
        return gia_tri
    if kieu == "mau":
        s = str(gia_tri or "").strip()
        if s and not (s.startswith("#") and len(s) in (4, 7)):
            raise HTTPException(400, f"Cài đặt {khoa} phải là mã màu dạng #RRGGBB")
        return s
    return "" if gia_tri is None else str(gia_tri)


@router.get("")
def lay_cai_dat(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return doc_cai_dat(db)


@router.get("/dang-ky")
def lay_dang_ky(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """Registry cài đặt đầy đủ cho giao diện tự sinh control theo đúng kiểu."""
    gia_tri = doc_cai_dat(db)
    da_luu = {dong.key: str(dong.updated_at) for dong in db.query(SystemSetting).all()}
    return {
        "nhom": [{"khoa_nhom": k, **v} for k, v in NHOM_CAI_DAT.items()],
        "cai_dat": [
            {**d, "gia_tri": gia_tri.get(d["khoa"], d["mac_dinh"]),
             "da_luu_luc": da_luu.get(d["khoa"])}
            for d in DANG_KY_CAI_DAT
        ],
    }


def _luu_mot_cai_dat(db: Session, khoa: str, gia_tri):
    dong = db.get(SystemSetting, khoa)
    if dong:
        dong.value = json.dumps(gia_tri, ensure_ascii=False)
    else:
        db.add(SystemSetting(key=khoa, value=json.dumps(gia_tri, ensure_ascii=False)))


def ap_dung_thay_doi(db: Session, thay_doi: dict) -> dict:
    """Áp dụng một tập thay đổi {khoa: gia_tri} với kiểm tra đầy đủ theo
    registry (khóa lạ -> 400, sai kiểu/ràng buộc -> 400). Dùng chung cho
    PUT /api/cai-dat và Trợ lý cấu hình qua chat (Đợt 3, mục 2) để mọi đường
    thay đổi cài đặt đều qua cùng một cổng kiểm tra."""
    for khoa, gia_tri in thay_doi.items():
        if khoa not in _THEO_KHOA:
            raise HTTPException(400, f"Khóa cài đặt không tồn tại: {khoa}")
        gia_tri = _kiem_tra_gia_tri(_THEO_KHOA[khoa], gia_tri)
        _luu_mot_cai_dat(db, khoa, gia_tri)
    db.commit()
    return doc_cai_dat(db)


@router.put("")
def cap_nhat_cai_dat(data: CaiDatIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    for khoa, gia_tri in data.model_dump(exclude_unset=True).items():
        if gia_tri is None or khoa not in _THEO_KHOA:
            continue
        gia_tri = _kiem_tra_gia_tri(_THEO_KHOA[khoa], gia_tri)
        _luu_mot_cai_dat(db, khoa, gia_tri)
    db.commit()
    return doc_cai_dat(db)


@router.get("/xem-prompt-tong-quat")
def xem_prompt_tong_quat(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Xem trước TOÀN VĂN prompt hệ thống mà bot sẽ ghép khi trả lời khách.

    Ghép bằng đúng hàm tao_cac_phan_prompt của ai_gateway với cài đặt hiện
    tại. Các phần phụ thuộc dữ liệu thật được nạp thật khi có (dịch vụ đang
    mở bán); phần phụ thuộc từng khách/từng câu hỏi dùng DỮ LIỆU MẪU ghi rõ
    [DỮ LIỆU MẪU] để quản trị viên thấy vị trí chúng sẽ xuất hiện.
    Trả về {cac_phan: [{ten, noi_dung, nguon}], toan_van}.
    """
    from ..models import ServiceItem
    from ..services.ai_gateway import tao_cac_phan_prompt
    cd = doc_cai_dat(db)
    # Dịch vụ THẬT đang mở bán (định dạng giống hệt orchestrator khi trả lời)
    try:
        so_dv = int(cd.get("so_dich_vu_pr") or 5)
    except (TypeError, ValueError):
        so_dv = 5
    dich_vu = []
    for s in (db.query(ServiceItem).filter(ServiceItem.is_active == True)
              .order_by(ServiceItem.id).limit(max(1, so_dv)).all()):
        gia = (s.price_text or "").strip()
        if not gia and s.price:
            gia = f"{s.price:,.0f}".replace(",", ".") + "đ"
        dich_vu.append({"ten": s.name, "gia": gia, "mo_ta": (s.description or "")[:200]})
    if not dich_vu:
        dich_vu = [{"ten": "[DỮ LIỆU MẪU] Dịch vụ mẫu (chưa có dịch vụ thật đang bật)",
                    "gia": "", "mo_ta": "Khi có dịch vụ thật đang mở bán, danh sách thật sẽ hiện ở đây thay cho dòng mẫu này."}]
    ho_so_mau = ("[DỮ LIỆU MẪU] Hồ sơ khách mẫu — khi trò chuyện thật, phần này là bản tóm tắt "
                 "bộ nhớ dài hạn của đúng khách đang nhắn (tên, nhu cầu, sở thích đã nhớ...).")
    chunks_mau = [{"content": "[DỮ LIỆU MẪU] Đoạn tri thức mẫu — khi trả lời thật, hệ thống truy hồi "
                              "các đoạn kho tri thức liên quan nhất tới câu hỏi của khách và đặt vào đây."}]
    ky_uc_mau = ["[DỮ LIỆU MẪU] Ký ức mẫu về khách — khi trả lời thật là các ký ức liên quan đã lưu trong Bộ nhớ AI."]
    cac_phan = tao_cac_phan_prompt(cd, chunks_mau, ky_uc_mau, dich_vu=dich_vu, ho_so_khach=ho_so_mau)
    return {"cac_phan": cac_phan, "toan_van": "\n".join(p["noi_dung"] for p in cac_phan)}


class KhoiPhucIn(BaseModel):
    nhom: Optional[str] = None


@router.post("/khoi-phuc-mac-dinh")
def khoi_phuc_mac_dinh(data: KhoiPhucIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Xóa giá trị đã lưu của một nhóm (hoặc tất cả) -> quay về mặc định registry."""
    if data.nhom and data.nhom not in NHOM_CAI_DAT:
        raise HTTPException(400, f"Nhóm cài đặt không tồn tại: {data.nhom}")
    khoa_can_xoa = [d["khoa"] for d in DANG_KY_CAI_DAT if not data.nhom or d["nhom"] == data.nhom]
    for khoa in khoa_can_xoa:
        dong = db.get(SystemSetting, khoa)
        if dong:
            db.delete(dong)
    db.commit()
    return doc_cai_dat(db)
