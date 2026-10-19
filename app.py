"""网易云息屏歌词 —— 主程序。

一个设置窗口 + 一个全屏黑色歌词覆盖层。
- 设置窗口：调整字体/字号/透明度/位置/颜色/光晕/侧边模糊/呼吸/流光等参数；
- 覆盖层：全屏黑底，按设置渲染歌词（中文 5 行、非中文 3 行+翻译）。

运行：`python app.py`（或双击 run.bat）。
"""

import atexit
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import webview

from netease import LyricProvider, restart_netease_debug

# 兼容源码运行与 PyInstaller 打包运行：
# - RESOURCE_DIR：只读资源（ui/）所在目录
# - DATA_DIR：可写数据（settings.json、错误日志）目录
if getattr(sys, "frozen", False):
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DATA_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = DATA_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = RESOURCE_DIR
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
SETTINGS_HTML = Path(os.path.join(RESOURCE_DIR, "ui", "settings.html")).as_uri()
OVERLAY_HTML = Path(os.path.join(RESOURCE_DIR, "ui", "overlay.html")).as_uri()
ERROR_LOG = os.path.join(DATA_DIR, "startup_error.log")

SETTINGS_TITLE = "网易云息屏歌词"
OVERLAY_TITLE = "息屏歌词·覆盖层"

DEFAULT_SETTINGS = {
    "font_family": "微软雅黑",
    "font_size": 110,
    "opacity": 100,
    "vertical_position": 50,
    "text_color": "#ffffff",
    "glow_color": "#4da6ff",
    "side_blur": 30,
    "breathing": True,
    "sweep": True,
}


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        if isinstance(data, dict):
            merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def coerce_settings(raw: dict) -> dict:
    s = dict(DEFAULT_SETTINGS)
    if isinstance(raw, dict):
        for k in DEFAULT_SETTINGS:
            if k in raw:
                s[k] = raw[k]
    try:
        s["font_size"] = max(12, min(200, int(s["font_size"])))
        s["opacity"] = max(10, min(100, int(s["opacity"])))
        s["vertical_position"] = max(0, min(100, int(s["vertical_position"])))
        s["side_blur"] = max(0, min(100, int(s["side_blur"])))
    except (TypeError, ValueError):
        s["font_size"] = DEFAULT_SETTINGS["font_size"]
        s["opacity"] = DEFAULT_SETTINGS["opacity"]
        s["vertical_position"] = DEFAULT_SETTINGS["vertical_position"]
        s["side_blur"] = DEFAULT_SETTINGS["side_blur"]
    s["font_family"] = str(s.get("font_family") or DEFAULT_SETTINGS["font_family"])
    s["text_color"] = str(s.get("text_color") or DEFAULT_SETTINGS["text_color"])
    s["glow_color"] = str(s.get("glow_color") or DEFAULT_SETTINGS["glow_color"])
    s["breathing"] = bool(s.get("breathing", True))
    s["sweep"] = bool(s.get("sweep", True))
    return s


def _debug_log(msg: str):
    try:
        with open(os.path.join(DATA_DIR, "debug.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


class Api:
    """暴露给前端 JS 的接口。"""

    def __init__(self, provider: LyricProvider, windows: dict):
        self.provider = provider
        self.windows = windows
        self.overlay_on = False
        self._hotkey_lock = threading.Lock()
        self._hotkey_pressed = False
        self._guard_thread = None

    # ---- 供前端调用 ----
    def get_settings(self):
        return load_settings()

    def get_state(self):
        state = self.provider.get_state()
        with self._hotkey_lock:
            if self._hotkey_pressed:
                self._hotkey_pressed = False
                state["request_close"] = True
        return state

    def start_overlay(self, settings):
        s = coerce_settings(settings)
        save_settings(s)
        with self._hotkey_lock:
            self._hotkey_pressed = False
        overlay = self.windows.get("overlay")
        if overlay is not None:
            self._place_overlay(0, 0)   # 显示并铺满全屏
            payload = json.dumps(s, ensure_ascii=False)
            try:
                overlay.evaluate_js(f"window.applySettings && window.applySettings({payload})")
            except Exception:
                pass
            self.overlay_on = True
            self._focus_overlay_later()
            self._keep_fullscreen()
        return True

    def _keep_fullscreen(self):
        """开启期间持续校正窗口尺寸，避免 WinForms 布局把窗口重置回初始大小。"""
        if self._guard_thread is not None and self._guard_thread.is_alive():
            return

        def _loop():
            while self.overlay_on:
                try:
                    self._place_overlay(0, 0)
                except Exception:
                    pass
                time.sleep(0.8)

        self._guard_thread = threading.Thread(target=_loop, daemon=True)
        self._guard_thread.start()

    def close_overlay(self, source="unknown"):
        _debug_log(f"close_overlay source={source}")
        overlay = self.windows.get("overlay")
        if overlay is not None:
            self._shrink_overlay()
        self.overlay_on = False
        # 退出息屏歌词后回到设置窗口
        settings = self.windows.get("settings")
        if settings is not None:
            try:
                settings.show()
            except Exception:
                pass
        return True

    def _shrink_overlay(self):
        """把覆盖层缩回 1x1（继续后台渲染，用户看不到）。"""
        try:
            import win32con
            import win32gui
            hwnd = win32gui.FindWindow(None, OVERLAY_TITLE)
            if hwnd:
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_NOTOPMOST, 0, 0, 1, 1,
                    win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED)
        except Exception:
            pass

    def _monitor_rect(self, hwnd):
        """在与 SetWindowPos 相同的线程/DPI 上下文中获取显示器全屏矩形。"""
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            u = ctypes.windll.user32
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            hmon = u.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            if hmon and u.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                r = mi.rcMonitor
                return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            pass
        return 0, 0, SCREEN_W, SCREEN_H

    def _place_overlay(self, x: int, y: int, offscreen: bool = False):
        """铺满当前显示器。

        关键：本机屏幕真实 2560x1600 @150%，不同 DPI 上下文中
        GetMonitorInfo/SetWindowPos 的单位不一致会导致窗口只有 2/3 屏。
        这里统一切到 per-monitor aware 上下文，用物理像素获取并设置尺寸。
        """
        try:
            import ctypes
            from ctypes import wintypes

            import win32con
            import win32gui

            hwnd = win32gui.FindWindow(None, OVERLAY_TITLE)
            if not hwnd:
                raise RuntimeError("no overlay hwnd")

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            u = ctypes.windll.user32
            old = u.SetThreadDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
            try:
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                hmon = u.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
                if hmon and u.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    mx, my = mi.rcMonitor.left, mi.rcMonitor.top
                    mw = mi.rcMonitor.right - mi.rcMonitor.left
                    mh = mi.rcMonitor.bottom - mi.rcMonitor.top
                else:
                    mx, my = 0, 0
                    mw, mh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
                _strip_window_chrome(hwnd)
                px = (mx - mw - 200) if offscreen else (mx + x)
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOPMOST, px, my + y, mw, mh,
                    win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED)
            finally:
                u.SetThreadDpiAwarenessContext(old)
            return
        except Exception:
            pass
        try:
            overlay = self.windows.get("overlay")
            if overlay is not None:
                overlay.move(x, y)
        except Exception:
            pass

    def quit_app(self):
        win = self.windows.get("settings")
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        return True

    def get_sync_status(self):
        """返回是否已连接网易云调试端口（精确同步）。"""
        return {"cdp": self.provider.cdp.get() is not None}

    def get_fonts(self):
        """枚举系统已安装的字体（中文字体优先）。"""
        fonts = set()

        def _cb(logfont, _tm, _ft, _param):
            try:
                name = logfont[0] if isinstance(logfont, (tuple, list)) else getattr(logfont, "lfFaceName", "")
                if name and not str(name).startswith("@"):
                    fonts.add(str(name))
            except Exception:
                pass
            return 1

        try:
            import win32gui
            hdc = win32gui.GetDC(0)
            try:
                win32gui.EnumFontFamilies(hdc, None, _cb, 0)
            finally:
                win32gui.ReleaseDC(0, hdc)
        except Exception:
            pass

        pref = [
            "微软雅黑", "微软雅黑 Light", "宋体", "新宋体", "黑体", "楷体", "仿宋",
            "等线", "等线 Light", "幼圆", "隶书", "微软正黑体",
            "华文细黑", "华文楷体", "华文宋体", "华文新魏", "华文行楷",
            "华文隶书", "华文琥珀", "华文彩云", "方正姚体", "方正舒体",
            "思源黑体", "思源宋体", "霞鹜文楷", "鸿蒙字体", "更纱黑体",
            "Arial", "Arial Black", "Segoe UI", "Segoe UI Light", "Calibri",
            "Cambria", "Consolas", "Georgia", "Impact", "Times New Roman",
            "Trebuchet MS", "Verdana",
        ]
        ordered = [f for f in pref if f in fonts]
        rest = sorted(f for f in fonts if f not in ordered)
        return ordered + rest

    def restart_netease_debug(self):
        """以调试模式重启网易云，用于歌词精确同步。"""
        return restart_netease_debug()

    # ---- 内部 ----
    def _focus_overlay_later(self):
        def _focus():
            try:
                import win32gui
                hwnd = win32gui.FindWindow(None, OVERLAY_TITLE)
                if hwnd:
                    _activate_window(hwnd)
            except Exception:
                pass
        threading.Timer(0.4, _focus).start()

    def _set_hotkey(self):
        with self._hotkey_lock:
            self._hotkey_pressed = True


def hotkey_thread(api: Api):
    """全局热键 Ctrl+Alt+Q：退出息屏歌词。"""
    try:
        import win32con
        import win32gui
        VK_Q = 0x51  # win32con 可能没有 VK_Q 常量
        win32gui.RegisterHotKey(None, 1, win32con.MOD_CONTROL | win32con.MOD_ALT, VK_Q)
        _debug_log("RegisterHotKey done")
        while True:
            msg = win32gui.GetMessage(None, 0, 0)
            if not msg:
                break
            # pywin32 返回 (hwnd, message, wParam, lParam)
            hwnd, message = msg[0], msg[1]
            if message == win32con.WM_HOTKEY:
                _debug_log(f"WM_HOTKEY received hwnd={hwnd}")
                api._set_hotkey()
    except Exception as e:  # noqa: BLE001
        _debug_log(f"hotkey_thread exception: {e!r}")


def _screen_size():
    try:
        import ctypes
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


SCREEN_W, SCREEN_H = _screen_size()
OFFSCREEN_X = SCREEN_W + 200

def _activate_window(hwnd: int):
    """可靠地把窗口带到前台（绕过 Windows 前台锁定）。"""
    try:
        import ctypes

        import win32gui
        if win32gui.GetForegroundWindow() == hwnd:
            return
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        if win32gui.GetForegroundWindow() == hwnd:
            return
        # 兜底：AttachThreadInput
        u = ctypes.windll.user32
        cur = ctypes.windll.kernel32.GetCurrentThreadId()
        fg = win32gui.GetForegroundWindow()
        fg_tid = win32gui.GetWindowThreadProcessId(fg)[0] if fg else 0
        thr_tid = win32gui.GetWindowThreadProcessId(hwnd)[0]
        a1 = a2 = False
        try:
            if fg_tid and fg_tid != cur:
                a1 = bool(u.AttachThreadInput(cur, fg_tid, True))
            if thr_tid and thr_tid != cur:
                a2 = bool(u.AttachThreadInput(cur, thr_tid, True))
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if a1:
                u.AttachThreadInput(cur, fg_tid, False)
            if a2:
                u.AttachThreadInput(cur, thr_tid, False)
    except Exception:
        pass


def _hide_from_taskbar(title: str):
    """把覆盖层从任务栏/Alt+Tab 中隐藏。"""
    try:
        import win32con
        import win32gui
        hwnd = win32gui.FindWindow(None, title)
        if not hwnd:
            return
        ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               ex | win32con.WS_EX_TOOLWINDOW)
    except Exception:
        pass


def _strip_window_chrome(hwnd: int):
    """去掉无边框窗口残留的标题栏/边框和 Win11 圆角阴影。"""
    try:
        import ctypes

        import win32con
        import win32gui
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

        dwm = ctypes.windll.dwmapi
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_DONOTROUND = 1
        v = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v), ctypes.sizeof(v))
        # DWMWA_BORDER_COLOR = 34, DWMWA_COLOR_NONE = 0xFFFFFFFE
        v2 = ctypes.c_uint(0xFFFFFFFE)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(v2), ctypes.sizeof(v2))
    except Exception:
        pass


def main():
    provider = LyricProvider()
    provider.start()
    atexit.register(provider.stop)

    windows: dict = {}
    api = Api(provider, windows)

    settings_win = webview.create_window(
        SETTINGS_TITLE,
        url=SETTINGS_HTML,
        js_api=api,
        width=560,
        height=880,
        min_size=(500, 640),
        resizable=True,
        background_color="#121317",
    )
    # 覆盖层：用 1x1 像素窗口常驻预加载（页面持续渲染运行），
    # 点击开启时铺满全屏。避免 hidden 窗口 WebView2 不渲染导致的黑屏。
    overlay_win = webview.create_window(
        OVERLAY_TITLE,
        url=OVERLAY_HTML,
        js_api=api,
        hidden=False,
        frameless=True,
        fullscreen=False,
        width=1,
        height=1,
        min_size=(1, 1),
        x=0,
        y=0,
        on_top=False,
        easy_drag=False,
        focus=False,
        background_color="#000000",
    )
    windows["settings"] = settings_win
    windows["overlay"] = overlay_win

    threading.Thread(target=hotkey_thread, args=(api,), daemon=True).start()

    def on_start():
        # 注意：不要用 webview.screens 覆盖屏幕尺寸——它受 DPI 缩放影响会偏小。
        time.sleep(0.8)
        _hide_from_taskbar(OVERLAY_TITLE)
        if os.environ.get("AOD_AUTO_OPEN") == "1":
            time.sleep(1.0)
            api.start_overlay(load_settings())

    webview.start(on_start, debug=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "程序启动失败，请查看 startup_error.log 了解详情。\n\n"
                "常见原因：系统缺少 Microsoft Edge WebView2 运行时。\n"
                "请安装：https://developer.microsoft.com/microsoft-edge/webview2/",
                "网易云息屏歌词", 0x10,
            )
        except Exception:
            pass
        sys.exit(1)
