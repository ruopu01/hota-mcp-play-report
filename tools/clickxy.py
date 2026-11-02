import ctypes, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp

user32 = ctypes.WinDLL("user32", use_last_error=True)
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def find_window():
    found = []

    def cb(hwnd, lparam):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if "Horn of the Abyss" in buf.value:
                found.append(hwnd)
        return True

    user32.EnumWindows(EnumProc(cb), None)
    return found[0] if found else None


x = int(sys.argv[1])
y = int(sys.argv[2])
hwnd = find_window()
lp = (y << 16) | x
user32.PostMessageW(hwnd, 0x0200, 0, lp)
time.sleep(0.2)
user32.PostMessageW(hwnd, 0x0201, 1, lp)
time.sleep(0.06)
user32.PostMessageW(hwnd, 0x0202, 0, lp)
time.sleep(0.8)
print("clicked", x, y)
