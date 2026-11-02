import ctypes, sys, time
from ctypes import wintypes
u = ctypes.windll.user32
found = []
def cb(hwnd, lp):
    if not u.IsWindowVisible(hwnd):
        return True
    n = u.GetWindowTextLengthW(hwnd)
    if n:
        b = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, b, n + 1)
        if "Horn of the Abyss" in b.value:
            found.append(hwnd)
    return True
u.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
if not found:
    print("no window"); sys.exit(1)
h = found[0]
vk = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x1B
scan = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x01
u.PostMessageW(h, 0x0100, vk, 0x00000001 | (scan << 16))
time.sleep(0.05)
u.PostMessageW(h, 0x0101, vk, 0xC0000001 | (scan << 16))
print("sent vk=0x%02X to hwnd %s" % (vk, h))
