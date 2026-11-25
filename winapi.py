"""Windows-only ctypes layer used by riot_client.py."""

import ctypes
import subprocess
import sys
import time
from contextlib import contextmanager
from ctypes import wintypes

SW_RESTORE = 9
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
VK_BACK, VK_TAB, VK_RETURN, VK_CONTROL, VK_MENU, VK_A = 0x08, 0x09, 0x0D, 0x11, 0x12, 0x41
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
DPI_AWARENESS_PER_MONITOR_AWARE_V2 = -4

# Process names that own the Riot Client window (compared in lower case).
RIOT_WINDOW_PROCESSES = ("riot client.exe", "riotclientux.exe")
RIOT_WINDOW_CLASS = "Chrome_WidgetWin_1"
MIN_WINDOW_SIZE = (400, 300)


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def _key_input(vk=0, scan=0, flags=0):
    item = _INPUT(type=INPUT_KEYBOARD)
    item.ki = _KEYBDINPUT(vk, scan, flags, 0, 0)
    return item


def _mouse_input(flags):
    item = _INPUT(type=INPUT_MOUSE)
    item.mi = _MOUSEINPUT(0, 0, 0, flags, 0, 0)
    return item


class WinApi:

    def __init__(self):
        if sys.platform != "win32":
            raise OSError("This part of AutoLogger only works on Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._bind()

    def _bind(self):
        u, k, g = self.user32, self.kernel32, self.gdi32
        self._enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u.EnumWindows.argtypes = [self._enum_proc, wintypes.LPARAM]
        u.EnumWindows.restype = wintypes.BOOL
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindowVisible.restype = wintypes.BOOL
        u.IsIconic.argtypes = [wintypes.HWND]
        u.IsIconic.restype = wintypes.BOOL
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.SetForegroundWindow.restype = wintypes.BOOL
        u.GetForegroundWindow.argtypes = []
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetClientRect.restype = wintypes.BOOL
        u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        u.ClientToScreen.restype = wintypes.BOOL
        u.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        u.SetCursorPos.restype = wintypes.BOOL
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.GetCursorPos.restype = wintypes.BOOL
        u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
        u.SendInput.restype = wintypes.UINT
        u.GetDC.argtypes = [wintypes.HWND]
        u.GetDC.restype = wintypes.HDC
        u.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        g.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        g.GetPixel.restype = wintypes.DWORD
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]

    @contextmanager
    def dpi_aware(self):
        """Use real screen pixels on this thread only (the Tk window stays as it was)."""
        function = getattr(self.user32, "SetThreadDpiAwarenessContext", None)
        previous = None
        if function is not None:
            function.argtypes = [ctypes.c_void_p]
            function.restype = ctypes.c_void_p
            previous = function(ctypes.c_void_p(DPI_AWARENESS_PER_MONITOR_AWARE_V2))
        try:
            yield
        finally:
            if function is not None and previous:
                function(previous)

    def _class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value

    def _process_name(self, hwnd):
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buffer))
            if self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return buffer.value.replace("/", "\\").rsplit("\\", 1)[-1].lower()
            return ""
        finally:
            self.kernel32.CloseHandle(handle)

    def find_window(self):
        """Handle of the Riot Client window, or None. Matches by process, not by title."""
        found = []

        def callback(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            if self._class_name(hwnd) != RIOT_WINDOW_CLASS:
                return True
            if self._process_name(hwnd) not in RIOT_WINDOW_PROCESSES:
                return True
            if self.user32.IsIconic(hwnd):
                found.append(hwnd)
                return True
            rect = self.client_rect(hwnd)
            if rect and rect[2] - rect[0] >= MIN_WINDOW_SIZE[0] and rect[3] - rect[1] >= MIN_WINDOW_SIZE[1]:
                found.append(hwnd)
            return True

        self.user32.EnumWindows(self._enum_proc(callback), 0)
        return found[0] if found else None

    def client_rect(self, hwnd):
        """(left, top, right, bottom) of the window's content area in screen pixels."""
        rect = wintypes.RECT()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        origin = wintypes.POINT(0, 0)
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            return None
        return (origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)

    def foreground_window(self):
        return self.user32.GetForegroundWindow()

    def set_foreground(self, hwnd, timeout=1.5):
        """Bring the window to the front (restoring it if minimized). True when it got focus."""
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.2)
        for attempt in range(2):
            self.user32.SetForegroundWindow(hwnd)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.user32.GetForegroundWindow() == hwnd:
                    return True
                time.sleep(0.05)
            # Windows sometimes refuses; tapping Alt lifts the restriction.
            self._send([_key_input(VK_MENU), _key_input(VK_MENU, flags=KEYEVENTF_KEYUP)])
        return self.user32.GetForegroundWindow() == hwnd

    def pixel(self, x, y):
        hdc = self.user32.GetDC(None)
        if not hdc:
            return None
        try:
            value = self.gdi32.GetPixel(hdc, int(x), int(y))
        finally:
            self.user32.ReleaseDC(None, hdc)
        if value == 0xFFFFFFFF:
            return None
        return (value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF)

    def _send(self, items):
        array = (_INPUT * len(items))(*items)
        sent = self.user32.SendInput(len(items), array, ctypes.sizeof(_INPUT))
        if sent != len(items):
            raise OSError(f"Windows blocked the keyboard/mouse input (sent {sent} of {len(items)}).")

    def cursor_pos(self):
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)

    def move_cursor(self, x, y):
        self.user32.SetCursorPos(int(x), int(y))

    def click(self, x, y):
        self.move_cursor(x, y)
        time.sleep(0.05)
        self._send([_mouse_input(MOUSEEVENTF_LEFTDOWN)])
        time.sleep(0.03)
        self._send([_mouse_input(MOUSEEVENTF_LEFTUP)])

    def _tap(self, vk):
        self._send([_key_input(vk), _key_input(vk, flags=KEYEVENTF_KEYUP)])

    def press_tab(self):
        self._tap(VK_TAB)

    def press_enter(self):
        self._tap(VK_RETURN)

    def clear_field(self):
        self._send([_key_input(VK_CONTROL), _key_input(VK_A),
                    _key_input(VK_A, flags=KEYEVENTF_KEYUP),
                    _key_input(VK_CONTROL, flags=KEYEVENTF_KEYUP)])
        self._tap(VK_BACK)

    def type_text(self, text, delay=0.01):
        """Type text as Unicode characters: independent of the keyboard layout."""
        data = text.encode("utf-16-le")
        for index in range(0, len(data), 2):
            unit = int.from_bytes(data[index:index + 2], "little")
            self._send([_key_input(scan=unit, flags=KEYEVENTF_UNICODE),
                        _key_input(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)])
            time.sleep(delay)

    def launch(self, executable, arguments=()):
        subprocess.Popen(
            [str(executable), *arguments],
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
