import ctypes, json, os, sys, time, uuid
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


def call(name, args=None, rid=2):
    s, _ = mcp.connect()
    res, _ = mcp.call(s, name, args or {}, rid=rid)
    return mcp.text_of(res)


def main():
    key = sys.argv[1]
    obs = json.loads(call("observe"))
    rev = obs["revision"]
    el = json.loads(call("inspect_element", {"element": key, "revision": rev}, rid=3))
    el = el["observation"]["elements"]
    target = next(e for e in el if e["key"] == key)
    cx = target["x"] + target["width"] // 2
    cy = target["y"] + target["height"] // 2
    hwnd = find_window()
    if not hwnd:
        print("window not found")
        return
    r = ctypes.wintypes.RECT() if hasattr(ctypes, "wintypes") else None
    import ctypes.wintypes as wt
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    cw, ch = r.right - r.left, r.bottom - r.top
    sw, sh = obs["width"], obs["height"]
    scale = min(cw / sw, ch / sh)
    ox = int((cw - sw * scale) / 2)
    oy = int((ch - sh * scale) / 2)
    wx = ox + int(cx * scale)
    wy = oy + int(cy * scale)
    print(f"client {cw}x{ch} surface {sw}x{sh} scale {scale:.3f} -> ({wx},{wy}) for {key} center ({cx},{cy})")
    lp = (wy << 16) | wx
    user32.PostMessageW(hwnd, 0x0200, 0, lp)
    time.sleep(0.2)
    user32.PostMessageW(hwnd, 0x0201, 1, lp)
    time.sleep(0.06)
    user32.PostMessageW(hwnd, 0x0202, 0, lp)
    time.sleep(0.6)
    print("clicked")


main()
