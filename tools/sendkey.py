"""Send a key press to the HoMM3 window via PostMessage (WM_KEYDOWN/WM_KEYUP).

usage: python sendkey.py <vk-hex> [<scan-hex>]
"""
import ctypes, sys, time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


def find_window(fragment="Horn of the Abyss"):
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if fragment.lower() in buf.value.lower():
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def main():
    vk = int(sys.argv[1], 16)
    scan = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    hwnd = find_window()
    if not hwnd:
        print("game window not found")
        return 1
    down = 1 | (scan << 16)
    up = down | 0xC0000000
    user32.PostMessageW(hwnd, 0x0100, vk, down)
    time.sleep(0.05)
    user32.PostMessageW(hwnd, 0x0101, vk, up)
    print(f"sent vk=0x{vk:02X} scan=0x{scan:02X} to hwnd {hwnd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
