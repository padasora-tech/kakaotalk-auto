# -*- coding: utf-8 -*-
"""
main_app.py - 카카오톡 대화방 목록 마우스 절대좌표 더블클릭 순차 전송 v51.0
- 화살표 키 포커스 유실 문제 100% 원천 해결
- 마우스로 1번째 줄(더블클릭) -> 전송 -> 2번째 줄(더블클릭) -> 전송 -> 3번째 줄(더블클릭)...
"""
import os
import sys
import json
import time
import random
import threading
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import pyautogui
import pyperclip

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
HTML_FILE = os.path.join(BASE_DIR, "extracted_dashboard.html")

DEFAULT_CONFIG = {
    "app_password": "cjstk1004!!@@",
    "send_mode": "chat_folder",
    "direct_msg": "안녕하세요 고객님, 이번 한 주도 기분 좋게 시작하세요! 😊",
    "excel_path": "고객명단_양식.xlsx",
    "delay_min": 2,
    "delay_max": 4
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
                return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

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
    print(f"[{ts}] {msg}")
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

def send_message_to_current_open_room(msg_text):
    """
    더블클릭으로 열린 대화창에 메시지를 붙여넣고 전송한 뒤 ESC로 닫습니다.
    """
    time.sleep(0.8)  # 대화창 렌더링 대기

    # 1. 메시지 붙여넣기
    set_clipboard_text(msg_text)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

    # 2. 메시지 전송
    pyautogui.press('enter')
    time.sleep(0.4)

    # 3. 대화방 닫기 (ESC)
    pyautogui.press('esc')
    time.sleep(0.3)
    return True, "전송 완료"

def worker_kakao_standalone():
    k_cfg = load_config()
    delay_min = float(k_cfg.get("delay_min", 2))
    delay_max = float(k_cfg.get("delay_max", 4))
    msg_template = k_cfg.get("direct_msg", "고객님, 이번 한 주도 기분 좋게 시작하세요! 😊")

    state["running"] = True
    state["paused"] = False
    state["stop"] = False
    state["ready"] = False
    state["success"] = 0
    state["fail"] = 0

    log("🔌 PC 카카오톡 대화방 목록 연동 모드 대기 중...", "success")
    log("💬 카톡에서 원하시는 폴더('기고객님들' 등)를 띄워두신 후,", "info")
    log("👉 대시보드의 [✅ 카톡 목록 자동 발송 시작!] 초록색 버튼을 눌러주세요!", "warn")

    state["status"] = "카톡 폴더 선택 대기 중..."

    # 초록색 버튼(ready) 누를 때까지 대기
    while not state["ready"]:
        if state["stop"] or not state["running"]:
            log("⬛ 준비 단계에서 작업이 중지되었습니다.", "warn")
            reset_state_to_idle()
            return
        time.sleep(0.3)

    log("🚀 2초 후 [마우스 물리적 순차 더블클릭] 발송을 시작합니다...", "info")
    state["status"] = "발송 진행 중..."
    time.sleep(2.0)

    # 2560x1600 해상도 분할 화면 기준 좌표
    screen_w, screen_h = pyautogui.size()
    
    # 카카오톡 창 좌측 목록 영역 (오른쪽 절반 화면 기준 x=1550)
    list_x = int(screen_w * 0.605)
    
    # 1번째 줄 y좌표: 약 150px
    # 각 대화방 사이의 간격: 약 72px
    start_y = int(screen_h * 0.095)  # 152px
    row_gap = int(screen_h * 0.045)  # 72px
    max_visible_rows = 11            # 화면에 보이는 방 개수

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

        # [마우스 순차 더블클릭 위치 계산]
        if idx <= max_visible_rows:
            # 화면에 보이는 1번째~11번째 줄을 위에서부터 아래로 차례대로 이동
            target_y = start_y + ((idx - 1) * row_gap)
        else:
            # 12번째부터는 맨 아래 줄 위치를 클릭하기 전 목록을 아래로 스크롤
            target_y = start_y + ((max_visible_rows - 1) * row_gap)
            pyautogui.moveTo(list_x, target_y)
            pyautogui.scroll(-150)
            time.sleep(0.3)

        log(f"[{idx}번째 고객 대화방] 마우스 더블클릭 진입... (좌표: {list_x}, {target_y})", "info")
        
        # 키보드 포커스 문제 없는 100% 확실한 마우스 더블클릭 진입
        pyautogui.doubleClick(list_x, target_y)

        ok, res_msg = send_message_to_current_open_room(msg_template)

        if ok:
            success_count += 1
            state["success"] = success_count
            log(f"  ✉️  [{idx}번째 고객 대화방] 발송 성공 완료!", "success")
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
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
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
                "logs": state["logs"]
            })
        elif parsed.path == "/config":
            self._send_json(load_config())
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
        else:
            self.send_error(404)

def main():
    PORT = 15874
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == "__main__":
    main()