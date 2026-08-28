# -*- coding: utf-8 -*-
"""
main_app.py - 카카오톡 대화방 목록 [마우스 순차 컨택(클릭) ➔ 엔터키(Enter) 대화창 짠 오픈 ➔ 텍스트+사진 전송 ➔ ESC 닫기] 최종본 v65.0
- 마우스 커서가 순차적으로 대화방을 1회 클릭하여 컨택(선택)
- 엔터키(Enter)를 눌러 채팅방을 짠 하고 오픈
- [텍스트 ➔ 사진] 순차 발송 후 ESC 닫기
- 바로 아래 채팅방으로 이동 반복
"""
import os
import sys
import json
import time
import random
import threading
import datetime
import io
import ctypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import pyautogui
import pyperclip
from PIL import Image
import win32clipboard

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 윈도우 커널 마우스 및 키보드 제어 API
user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B

def win32_move_mouse_smooth(target_x, target_y, steps=8):
    """마우스 커서가 눈에 보이도록 목표 지점으로 부드럽게 실시간 이동시킵니다."""
    try:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        curr_x, curr_y = pt.x, pt.y

        for step in range(1, steps + 1):
            ix = int(curr_x + (target_x - curr_x) * (step / steps))
            iy = int(curr_y + (target_y - curr_y) * (step / steps))
            user32.SetCursorPos(ix, iy)
            time.sleep(0.015)
        user32.SetCursorPos(target_x, target_y)
    except Exception:
        pass

def win32_contact_room(x, y):
    """마우스로 해당 대화방 위치를 딱 1번 클릭하여 카톡 창 활성화 및 대화방을 컨택(선택)합니다."""
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.15)  # 컨택 선택 완료 대기

def win32_press_enter():
    """엔터키를 눌러 선택된 대화방을 짠 하고 엽니다."""
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    pyautogui.press('enter')  # 2중 보조 엔터

def win32_scroll_down(amount=-180):
    """카카오톡 대화방 목록을 아래로 스크롤합니다."""
    try:
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
    except Exception:
        pass

pyautogui.PAUSE = 0.04
pyautogui.FAILSAFE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
HTML_FILE = os.path.join(BASE_DIR, "extracted_dashboard.html")
TEMP_IMAGE_PATH = os.path.join(BASE_DIR, "temp_attached_image.png")

DEFAULT_CONFIG = {
    "app_password": "cjstk1004!!@@",
    "send_mode": "chat_folder",
    "direct_msg": "2026년 8월 28일 금요일 소식 전해 드립니다♡",
    "excel_path": "고객명단_양식.xlsx",
    "delay_min": 2,
    "delay_max": 4,
    "has_image": True
}

state = {
    "running": False,
    "paused": False,
    "stop": False,
    "ready": False,
    "total": 0,
    "success": 0,
    "fail": 0,
    "status": "대기 중",
    "logs": []
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(loaded)
                cfg["has_image"] = os.path.exists(TEMP_IMAGE_PATH)
                return cfg
        except Exception:
            pass
    cfg = DEFAULT_CONFIG.copy()
    cfg["has_image"] = os.path.exists(TEMP_IMAGE_PATH)
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def log(msg, level="info"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {"time": ts, "msg": str(msg), "level": level}
    try:
        print(f"[{ts}] {msg}")
    except Exception:
        pass
    state["logs"].append(entry)
    if len(state["logs"]) > 300:
        state["logs"].pop(0)

def reset_state_to_idle():
    state["running"] = False
    state["paused"] = False
    state["stop"] = False
    state["ready"] = False
    state["status"] = "대기 중"

def interruptible_sleep(seconds):
    end_time = time.time() + seconds
    while time.time() < end_time:
        if state["stop"] or not state["running"]:
            break
        time.sleep(0.1)

def set_clipboard_text(text):
    for _ in range(5):
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            if pyperclip.paste() == text:
                return True
        except Exception:
            time.sleep(0.05)
    return True

def set_clipboard_image(image_path):
    """윈도우 클립보드에 이미지(DIB)를 복사하여 카카오톡에 Ctrl+V로 붙여넣을 수 있게 합니다."""
    try:
        img = Image.open(image_path)
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        log(f"이미지 클립보드 복사 실패: {e}", "error")
        return False

def send_message_to_opened_room(msg_text="", image_path=None):
    """
    열린 대화창에 [텍스트 ➔ 사진]을 순서대로 전송하고 ESC로 대화창을 닫습니다.
    """
    time.sleep(0.8)  # 대화창 렌더링 대기

    # 1. 텍스트 전송
    if msg_text and msg_text.strip():
        set_clipboard_text(msg_text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.25)
        pyautogui.press('enter')  # 텍스트 전송
        time.sleep(0.4)

    # 2. 사진(카드뉴스) 전송
    if image_path and os.path.exists(image_path):
        if set_clipboard_image(image_path):
            time.sleep(0.15)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.35)
            pyautogui.press('enter')  # 사진 전송
            time.sleep(0.45)

    # 3. 대화방 닫기 (ESC) -> 대화방 목록으로 포커스 복귀
    pyautogui.press('esc')
    time.sleep(0.4)  # 포커스 복귀 대기
    return True, "전송 완료"

def worker_kakao_standalone():
    k_cfg = load_config()
    delay_min = float(k_cfg.get("delay_min", 2))
    delay_max = float(k_cfg.get("delay_max", 4))
    msg_template = k_cfg.get("direct_msg", "2026년 8월 28일 금요일 소식 전해 드립니다♡")
    
    image_to_send = TEMP_IMAGE_PATH if os.path.exists(TEMP_IMAGE_PATH) else None

    state["running"] = True
    state["paused"] = False
    state["stop"] = False
    state["ready"] = False
    state["success"] = 0
    state["fail"] = 0

    log("🔌 PC 카카오톡 대화방 목록 연동 모드 대기 중...", "success")
    if image_to_send:
        log("📸 [텍스트 ➔ 사진 콤보 발송] 첨부된 카드뉴스 사진이 준비되었습니다.", "info")
    log("💬 카톡 우측의 [기고객님들] 폴더를 띄워두신 후,", "info")
    log("👉 대시보드의 [✅ 카톡 목록 준비 완료! 자동 발송 시작!] 초록색 버튼을 눌러주세요!", "warn")

    state["status"] = "카톡 폴더 선택 대기 중..."

    # 초록색 버튼(ready) 누를 때까지 대기
    while not state["ready"]:
        if state["stop"] or not state["running"]:
            log("⬛ 준비 단계에서 작업이 중지되었습니다.", "warn")
            reset_state_to_idle()
            return
        time.sleep(0.2)

    log("🚀 2초 후 1번째 대화방부터 [컨택 ➔ 엔터 오픈 ➔ 텍스트+사진 전송 ➔ ESC ➔ 다음 방]을 시작합니다...", "info")
    state["status"] = "발송 진행 중..."
    time.sleep(2.0)

    # 2560x1600 해상도 분할 화면 기준 좌표
    screen_w, screen_h = pyautogui.size()
    list_x = int(screen_w * 0.605)    # 약 1548px (대화방 이름 영역)
    start_y = int(screen_h * 0.095)   # 약 152px (1번째 대화방 Y좌표)
    row_gap = int(screen_h * 0.045)   # 약 72px (각 대화방 간격)
    max_visible_rows = 11             # 화면에 보이는 방 개수

    max_limit = 500
    state["total"] = max_limit
    success_count = 0

    for idx in range(1, max_limit + 1):
        if state["stop"] or not state["running"]:
            log("⬛ 사용자에 의해 중지되었습니다.", "warn")
            break

        while state["paused"]:
            log("⏸️ 일시정지 됨", "warn")
            time.sleep(0.5)
            if state["stop"] or not state["running"]:
                break

        # [마우스 순차 이동 위치 계산]
        if idx <= max_visible_rows:
            target_y = start_y + ((idx - 1) * row_gap)
        else:
            target_y = start_y + ((max_visible_rows - 1) * row_gap)
            win32_move_mouse_smooth(list_x, target_y, steps=6)
            win32_scroll_down(-180)
            time.sleep(0.3)

        log(f"[{idx}번째 고객 대화방] 마우스 이동 ➔ 컨택(클릭) ➔ 엔터키로 대화창 짠 오픈...", "info")
        
        # 1. 마우스 커서를 목표 대화방으로 부드럽게 이동
        win32_move_mouse_smooth(list_x, target_y, steps=8)
        
        # 2. 마우스로 딱 1회 클릭하여 대화방 컨택(선택)
        win32_contact_room(list_x, target_y)

        # 3. 엔터키(Enter)를 눌러 대화창을 짠! 하고 오픈
        win32_press_enter()

        # 4. 열린 대화창에 [텍스트 ➔ 사진] 전송 후 ESC 닫기
        ok, res_msg = send_message_to_opened_room(msg_template, image_to_send)

        if ok:
            success_count += 1
            state["success"] = success_count
            log(f"  ✉️ [{idx}번째 고객 대화방] 발송 성공 완료! (ESC 닫고 다음 방으로)", "success")
        else:
            state["fail"] += 1
            log(f"  ❌ [{idx}번째 대화방] 전송 오류: {res_msg}", "error")

        wait_sec = random.uniform(delay_min, delay_max)
        log(f"  ⏳ 다음 발송까지 안전 대기 중... ({wait_sec:.1f}초)")
        interruptible_sleep(wait_sec)

    log("========================================", "info")
    log(f"🎉 [카카오톡 전원 자동 전송 완료] 총 {state['success']}개 대화방 전송 성공!", "success")
    log("========================================", "info")
    reset_state_to_idle()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            if os.path.exists(HTML_FILE):
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "<h1>Dashboard Not Found</h1>"
            self._send_html(content)
        elif parsed.path == "/status":
            self._send_json({
                "running": state["running"],
                "paused": state["paused"],
                "ready": state["ready"],
                "total": state["total"],
                "success": state["success"],
                "fail": state["fail"],
                "status": state["status"],
                "logs": state["logs"],
                "has_image": os.path.exists(TEMP_IMAGE_PATH)
            })
        elif parsed.path == "/config":
            self._send_json(load_config())
        elif parsed.path == "/preview_image":
            if os.path.exists(TEMP_IMAGE_PATH):
                with open(TEMP_IMAGE_PATH, "rb") as f:
                    img_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(img_data)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(img_data)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/auth":
            try:
                body = json.loads(self._read_body().decode("utf-8"))
                cfg = load_config()
                req_pass = cfg.get("app_password", "cjstk1004!!@@")
                if body.get("password") == req_pass:
                    self._send_json({"ok": True})
                else:
                    self._send_json({"ok": False, "msg": "비밀번호 불일치"}, 401)
            except Exception as e:
                self._send_json({"ok": False, "msg": str(e)}, 400)
        elif parsed.path == "/start":
            if not state["running"]:
                t = threading.Thread(target=worker_kakao_standalone, daemon=True)
                t.start()
            self._send_json({"ok": True})
        elif parsed.path == "/ready":
            state["ready"] = True
            if not state["running"]:
                t = threading.Thread(target=worker_kakao_standalone, daemon=True)
                t.start()
            self._send_json({"ok": True})
        elif parsed.path == "/pause":
            try:
                body = json.loads(self._read_body().decode("utf-8"))
                state["paused"] = body.get("pause", not state["paused"])
            except Exception:
                state["paused"] = not state["paused"]
            self._send_json({"ok": True, "paused": state["paused"]})
        elif parsed.path == "/stop":
            state["stop"] = True
            state["running"] = False
            state["paused"] = False
            state["ready"] = False
            state["status"] = "대기 중"
            self._send_json({"ok": True})
        elif parsed.path == "/config":
            try:
                body = json.loads(self._read_body().decode("utf-8"))
                cfg = load_config()
                cfg.update(body)
                save_config(cfg)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 400)
        elif parsed.path == "/api/upload_image":
            try:
                raw_bytes = self._read_body()
                with open(TEMP_IMAGE_PATH, "wb") as f:
                    f.write(raw_bytes)
                log("📸 새로운 사진/이미지가 성공적으로 첨부되었습니다.", "success")
                self._send_json({"ok": True, "msg": "이미지 업로드 성공"})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
        elif parsed.path == "/api/clear_image":
            try:
                if os.path.exists(TEMP_IMAGE_PATH):
                    os.remove(TEMP_IMAGE_PATH)
                log("🗑️ 첨부된 사진이 제거되었습니다. (텍스트 단독 발송 모드)", "info")
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
        else:
            self.send_error(404)

def start_server_on_port(port):
    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
        server.serve_forever()
    except Exception:
        pass

def main():
    ports = [15874, 15888, 15890]
    for p in ports:
        t = threading.Thread(target=start_server_on_port, args=(p,), daemon=True)
        t.start()
        try:
            print(f"[Kakao Customer Manager] Listening on http://127.0.0.1:{p}")
        except Exception:
            pass
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()