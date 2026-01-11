import json
import sys
import time
from ctypes import windll

import webview

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000


def set_window_opacity(hwnd, opacity):
    try:
        # opacity is 0-1.0, map to 0-255
        alpha = int(opacity * 255)
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
    except Exception:
        pass


def set_window_borderless(hwnd, borderless):
    try:
        style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        if borderless:
            style &= ~(WS_CAPTION | WS_THICKFRAME)
        else:
            style |= (WS_CAPTION | WS_THICKFRAME)
        windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        # Trigger frame redraw
        windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
    except Exception:
        pass


def api_listener(window):
    # Wait for window to be ready
    time.sleep(1)

    # Try to get HWND
    hwnd = None

    for line in sys.stdin:
        try:
            cmd = json.loads(line)
            action = cmd.get("action")

            if action == "navigate":
                window.load_url(cmd["url"])

            elif action == "set_title":
                window.set_title(cmd["title"])

            elif action == "set_opacity":
                # Try to find HWND if not found
                if not hwnd:
                    # Best effort: FindWindow by Title
                    # Note: Title might have changed.
                    cur_title = cmd.get("current_title", window.title)
                    hwnd = windll.user32.FindWindowW(None, cur_title)

                if hwnd:
                    set_window_opacity(hwnd, float(cmd["value"]))

            elif action == "set_borderless":
                if not hwnd:
                    cur_title = cmd.get("current_title", window.title)
                    hwnd = windll.user32.FindWindowW(None, cur_title)
                if hwnd:
                    set_window_borderless(hwnd, bool(cmd["value"]))

            elif action == "eval_js":
                window.evaluate_js(cmd["code"])

            elif action == "quit":
                window.destroy()
                break

        except Exception:
            pass


def run(title, url):
    # Create window
    # frameless=False initially, let logic handle it or user choice
    window = webview.create_window(title, url, width=1000, height=750)
    webview.start(api_listener, window)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    title = args[0] if len(args) > 0 else "Browser"
    url = args[1] if len(args) > 1 else "https://www.zhihu.com"
    run(title, url)


if __name__ == "__main__":
    main()
