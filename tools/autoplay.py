import ctypes, json, os, sys, time, uuid
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp

user32 = ctypes.windll.user32
LOGPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autoplay.log")

PICK = {
    "resource", "treasure_chest", "windmill", "water_wheel", "garden_of_revelation",
    "fountain_of_fortune", "mineral_spring", "rally_flag", "sign", "obelisk",
    "learning_stone", "tree_of_knowledge", "stables", "mystical_garden",
    "artifact", "sea_chest", "shipwreck", "corpse", "lean_to", "scholar",
}

ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


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

    user32.EnumWindows(ENUM_PROC(cb), 0)
    return found[0] if found else None


def send_key(vk, scan):
    h = find_window()
    if not h:
        return False
    user32.PostMessageW(h, 0x0100, vk, (scan << 16) | 1)
    time.sleep(0.1)
    user32.PostMessageW(h, 0x0101, vk, 0xC0000000 | (scan << 16) | 1)
    return True


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    with open(LOGPATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


class Game:
    def __init__(self):
        self.s, _ = mcp.connect()
        self.rid = 10

    def call(self, name, args=None):
        self.rid += 1
        res, raw = mcp.call(self.s, name, args or {}, rid=self.rid)
        return mcp.text_of(res)

    def obs(self, tries=3):
        for _ in range(tries):
            txt = self.call("observe")
            try:
                return json.loads(txt)
            except Exception:
                time.sleep(0.5)
        return None

    def act(self, action):
        txt = ""
        for _ in range(3):
            o = self.obs()
            if not o:
                return "no observation"
            txt = self.call("act", {"operationId": str(uuid.uuid4()), "revision": o["revision"], "action": action})
            if "STALE_REVISION" not in txt:
                return txt
            time.sleep(0.3)
        return txt

    def click(self, element, o):
        return self.call("click_ui", {"operationId": str(uuid.uuid4()), "revision": o["revision"], "element": element})

    def move(self, target_id):
        r = ""
        for _ in range(3):
            o = self.obs()
            if not o:
                return "no observation"
            txt = self.call("nearby_targets", {"revision": o["revision"]})
            try:
                near = json.loads(txt)
            except Exception:
                time.sleep(0.4)
                continue
            r = self.call("move_to", {"operationId": str(uuid.uuid4()),
                                      "revision": near["revision"], "targetId": target_id})
            if "STALE" not in r:
                return r
            time.sleep(0.4)
        return r or "move failed"


def settle(g, rounds=14):
    clicked = set()
    for _ in range(rounds):
        o = g.obs()
        if not o:
            return None
        s = o.get("screen")
        if s == "adventure":
            return o
        if s in ("victory", "defeat"):
            return o
        if s == "message":
            els = o.get("elements") or []
            order = []
            gold = next((e for e in els if "resour" in (e.get("asset") or "")), None)
            if gold:
                order.append(gold["key"])
            ok = next((e for e in els if "iokay" in (e.get("asset") or "")), None)
            if ok:
                order.append(ok["key"])
            for a in (o.get("actions") or []):
                order.append(a["key"])
            for key in order:
                if key in clicked:
                    continue
                clicked.add(key)
                if key.startswith("ui:"):
                    g.click(key, o)
                else:
                    g.act(key)
                break
            else:
                send_key(0x1B, 0x01)
                time.sleep(0.5)
            continue
        if s == "combat":
            log("  combat -> " + g.act("combat:auto")[:60])
            continue
        if s == "battle_result":
            log("  battle result -> " + g.act("battle:accept")[:60])
            continue
        if s == "town":
            g.act("town:close")
            continue
        if s == "recruitment":
            g.act("recruit:cancel")
            continue
        if s == "popup_choice":
            g.act("popup:锌芯写褌胁械褉写懈褌褜")
            continue
        send_key(0x1B, 0x01)
        time.sleep(0.5)
    return None


def status(o):
    h = o.get("hero") or {}
    t = (o.get("towns") or [{}])[0]
    return "d%s gold=%s mp=%s at=%s army=%s built=%s" % (
        o.get("date"), (o.get("resources") or [0] * 7)[6], h.get("movement"),
        h.get("position"), h.get("army"), len(t.get("built") or []))


def main():
    g = Game()
    bad = set()
    used = set()
    week = None
    days = 0
    moves = 0
    t0 = time.time()
    while days < 900:
        o = settle(g)
        if not o:
            log("settle failed; esc")
            send_key(0x1B, 0x01)
            time.sleep(1)
            continue
        if o.get("screen") in ("victory", "defeat"):
            log("GAME OVER: " + o["screen"])
            break
        h = o.get("hero") or {}
        if not h:
            log("no hero on map; waiting 30s")
            time.sleep(30)
            continue

        for step in range(25):
            if (h.get("movement") or 0) <= 0:
                break
            try:
                near = json.loads(g.call("nearby_targets", {"revision": o["revision"]}))
            except Exception:
                break
            cands = []
            for t in near.get("targets") or []:
                rt = t.get("route") or {}
                det = rt.get("detail") or ""
                if t.get("kind") not in PICK or t["id"] in bad or t["id"] in used:
                    continue
                if "fog of war" in det or "за водой" in det or "отрезана" in det:
                    continue
                score = (0 if rt.get("state") == "reachable_today" else 1, rt.get("steps") or 99)
                cands.append((score, t))
            if not cands:
                break
            cands.sort(key=lambda x: x[0])
            score, t = cands[0]
            txt = g.move(t["id"])
            log(status(o) + " -> %s %s (%s,%s) : %s" % (t.get("kind"), t.get("name"),
                                                        t.get("x"), t.get("y"), txt[:60]))
            if '"status":"completed"' in txt or "uncertain" in txt:
                moves += 1
                bad.add(t["id"])
                used.add(t["id"])
            else:
                bad.add(t["id"])
            o = settle(g)
            if not o:
                break
            if o.get("screen") in ("victory", "defeat"):
                log("GAME OVER: " + o["screen"])
                return
            h = o.get("hero") or {}
            if not h:
                break

        wk = tuple(o.get("date") or [0, 0, 0])[1]
        if wk != week:
            week = wk
            used.clear()
        r = g.act("turn:end")
        log(status(o) + " | end turn : " + r[:60])
        days += 1
        bad.clear()
        if days % 10 == 0:
            log("== run day %d, %d moves, %.0f min ==" % (days, moves, (time.time() - t0) / 60))
    log("done: %d days, %d moves, %.0fs" % (days, moves, time.time() - t0))


if __name__ == "__main__":
    main()

