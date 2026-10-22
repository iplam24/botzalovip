"""Bộ kết nối Zalo: interface trừu tượng, Mock và OA Stub (không giả kết nối thật)."""
from abc import ABC, abstractmethod

class ZaloConnector(ABC):
    @abstractmethod
    def connect(self): pass
    @abstractmethod
    def disconnect(self): pass
    @abstractmethod
    def status(self): pass
    @abstractmethod
    def send_text(self, conversation_external_id: str, text: str): pass
    def send_image(self, cid, url): raise NotImplementedError("Chưa hỗ trợ gửi hình ảnh")
    def react(self, mid, icon): raise NotImplementedError("Chưa hỗ trợ thả cảm xúc")
    def send_sticker(self, cid, sid): raise NotImplementedError("Chưa hỗ trợ gửi sticker")
    def get_conversation(self, cid): return {"id": cid}

class MockZaloConnector(ZaloConnector):
    def __init__(self): self.connected = True; self.sent = []
    def connect(self): self.connected = True; return {"trang_thai": "da_ket_noi", "moi_truong": "mo_phong"}
    def disconnect(self): self.connected = False; return {"trang_thai": "da_ngat"}
    def status(self): return {"trang_thai": "da_ket_noi" if self.connected else "mat_ket_noi", "moi_truong": "mo_phong", "ho_tro": ["send_text"]}
    def send_text(self, cid, text):
        if not self.connected: raise RuntimeError("Connector mất kết nối (mô phỏng)")
        self.sent.append((cid, text)); return {"thanh_cong": True, "mo_phong": True}

class ZaloOAStubConnector(ZaloConnector):
    """Zalo OA cần token OA/app chính thức. Thiếu token thì báo CHƯA HỖ TRỢ, không fake."""
    def __init__(self, token=""): self.token = token
    def connect(self):
        if not self.token: return {"trang_thai": "chua_ho_tro", "thong_bao": "CHƯA HỖ TRỢ: Cần token Zalo OA và app đã được phê duyệt"}
        return {"trang_thai": "chua_kiem_thu", "thong_bao": "Có token nhưng stub chưa gọi API thật trong MVP"}
    def disconnect(self): return {"trang_thai": "da_ngat"}
    def status(self): return {"trang_thai": "chua_ho_tro" if not self.token else "chua_kiem_thu", "ho_tro": []}
    def send_text(self, cid, text): raise RuntimeError("CHƯA HỖ TRỢ: Zalo OA stub chưa kết nối API thật - cần cấu hình OA token")

mock_connector = MockZaloConnector()

import os, httpx

class ZaloPersonalConnector(ZaloConnector):
    """Adapter tới sidecar Node zca-js (connectors/zalo-personal).

    Đây là thư viện KHÔNG chính thức cho tài khoản cá nhân. Nếu sidecar
    chưa chạy / offline, trạng thái bắt buộc là mất kết nối - không fake
    "đã kết nối". URL đọc từ env ZALO_PERSONAL_SERVICE_URL.
    """
    OFFLINE = {"trang_thai": "mat_ket_noi", "thong_bao": "Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân", "moi_truong": "ca_nhan_sidecar"}
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or os.getenv("ZALO_PERSONAL_SERVICE_URL") or "http://localhost:8791").rstrip("/")
    def _call(self, method: str, path: str, json_data=None):
        # Sidecar là dịch vụ nội bộ: đi trực tiếp, không qua proxy môi trường
        with httpx.Client(timeout=8, trust_env=False) as client:
            r = client.request(method, f"{self.base_url}{path}", json=json_data)
            try: data = r.json()
            except Exception: data = {"thong_bao": r.text[:200]}
            return r.status_code, data
    def status(self):
        try:
            code, data = self._call("GET", "/trang-thai")
            if code >= 400: return {**self.OFFLINE, "chi_tiet": data}
            return data
        except Exception:
            return dict(self.OFFLINE)
    def connect(self):
        """Bắt đầu đăng nhập QR - proxy POST /dang-nhap-qr của sidecar."""
        try:
            code, data = self._call("POST", "/dang-nhap-qr")
            if code >= 400: return {"trang_thai": "loi", "thong_bao": data.get("thong_bao", "Sidecar trả lỗi"), "chi_tiet": data}
            return data
        except Exception:
            return {**self.OFFLINE, "trang_thai": "mat_ket_noi"}
    def disconnect(self):
        try:
            code, data = self._call("POST", "/ngat-ket-noi")
            if code >= 400: return {"trang_thai": "loi", "thong_bao": data.get("thong_bao", "Không ngắt được kết nối"), "chi_tiet": data}
            return data
        except Exception:
            return dict(self.OFFLINE)
    def send_text(self, cid, text):
        try:
            code, data = self._call("POST", "/gui-tin-nhan", {"thread_id": str(cid), "content": text})
        except Exception as e:
            raise RuntimeError("Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân") from e
        if code >= 400: raise RuntimeError(data.get("thong_bao", f"Sidecar trả lỗi {code}"))
        return data
    def send_image(self, cid, url): raise NotImplementedError("Chưa hỗ trợ gửi hình ảnh qua Zalo cá nhân")
    def react(self, message_id, icon=""):
        try:
            code, data = self._call("POST", "/tha-cam-xuc", {"message_id": str(message_id), "icon": icon})
        except Exception as e:
            raise RuntimeError("Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân") from e
        if code == 501: raise NotImplementedError(data.get("thong_bao", "Thư viện zca-js không hỗ trợ thả cảm xúc trong bản hiện tại"))
        if code >= 400: raise RuntimeError(data.get("thong_bao", f"Sidecar trả lỗi {code}"))
        return data
    def send_sticker(self, cid, sticker_id=""):
        try:
            code, data = self._call("POST", "/gui-sticker", {"thread_id": str(cid), "sticker_id": str(sticker_id)})
        except Exception as e:
            raise RuntimeError("Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân") from e
        if code == 501: raise NotImplementedError(data.get("thong_bao", "Thư viện zca-js không hỗ trợ gửi sticker trong bản hiện tại"))
        if code >= 400: raise RuntimeError(data.get("thong_bao", f"Sidecar trả lỗi {code}"))
        return data
    def get_conversation(self, cid): return {"id": cid, "nguon": "ca_nhan_sidecar"}
