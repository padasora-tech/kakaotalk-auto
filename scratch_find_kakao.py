import ctypes
from ctypes import wintypes
import win32gui
import win32process

user32 = ctypes.windll.user32

def enum_all_visible():
    results = []
    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            
            cls_buff = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buff, 256)
            cls_name = cls_buff.value
            
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w > 100 and h > 100:
                results.append((hwnd, title, cls_name, rect))
    win32gui.EnumWindows(enum_cb, None)
    for r in results:
        print(f"HWND: {r[0]}, Title: '{r[1]}', Class: '{r[2]}', Rect: {r[3]}")

enum_all_visible()
