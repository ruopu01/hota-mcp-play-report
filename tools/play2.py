import json, os, sys, time, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp


def call(name, args=None, rid=2):
    s, _ = mcp.connect()
    res, _ = mcp.call(s, name, args or {}, rid=rid)
    t = mcp.text_of(res)
    return res, t


def jobserve():
    res, t = call("observe")
    try:
        return json.loads(t)
    except Exception:
        print("observe raw:", t[:200].replace("\n", " "))
        return None


def act(action):
    o = jobserve()
    if not o:
        return None
    res, t = call("act", {"operationId": "probe-" + uuid.uuid4().hex[:10],
                          "revision": o["revision"], "action": action}, rid=3)
    try:
        j = json.loads(t)
        print("act", action, "->", j.get("status"), "|", j.get("message"))
    except Exception:
        print("act", action, "-> RAW", t[:200].replace("\n", " "))
    time.sleep(1)
    return jobserve()


def state():
    o = jobserve()
    if not o:
        return None
    print("screen:", o["screen"], "| rev:", o["revision"], "| date:", o.get("date"), "| gold:", (o.get("resources") or [None] * 7)[6])
    for h in o.get("heroes") or []:
        print("  hero:", h["name"], h["position"], "mp", h["movement"], "/", h["maxMovement"], "|", ", ".join(h.get("army") or []))
    for t in o.get("towns") or []:
        print("  town:", t["name"], t["position"], "| built:", len(t.get("built") or []), "| recruitable:", t.get("recruitable"))
    return o


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    if cmd == "state":
        state()
    elif cmd == "plan":
        text = open(sys.argv[2], encoding="utf-8").read()
        res, t = call("plan", {"value": text})
        print(t[:600])
    elif cmd == "near":
        res, t = call("nearby_targets")
        try:
            j = json.loads(t)
            print("rev:", j["revision"], "movement:", j.get("movement"))
            for tg in j["targets"]:
                r = tg.get("route") or {}
                print("  ", tg["x"], tg["y"], tg["kind"], "|", tg["name"], "|", r.get("state"),
                      (r.get("detail") or "")[-60:], "| steps", r.get("steps"), "mp", r.get("movement"))
        except Exception:
            print(t[:800])
    elif cmd == "act":
        act(sys.argv[2])
    elif cmd == "move":
        x, y = sys.argv[2], sys.argv[3]
        res, t = call("move_to", {"x": x, "y": y, "z": 0})
        print("move_to", x, y, "->", t[:400].replace("\n", " "))
    elif cmd == "endturn":
        act("turn:end")
        o = jobserve()
        if o and o["screen"] == "message":
            print("message actions:", [a["key"] for a in o.get("actions", [])])
            for a in o.get("actions", []):
                if "confirm" in a["key"] or "accept" in a["key"]:
                    act(a["key"])
                    break
        state()
    elif cmd == "go":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        z = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        res, t = call("nearby_targets")
        j = json.loads(t)
        tgt = None
        for tg in j["targets"]:
            if tg["x"] == x and tg["y"] == y and tg.get("z", 0) == z:
                tgt = tg
                break
        if not tgt:
            print("no target at", x, y)
            sys.exit(0)
        print("target:", tgt["kind"], tgt["name"], "route:", (tgt.get("route") or {}).get("state"))
        res, t2 = call("move_to", {"operationId": "probe-" + uuid.uuid4().hex[:10],
                                   "revision": j["revision"], "targetId": tgt["id"]})
        print("move_to ->", t2[:500].replace("\n", " "))
        time.sleep(1)
        o = state()
        if o:
            print("actions now:", [a["key"] for a in o.get("actions", [])][:12])
    elif cmd == "click":
        o = jobserve()
        if not o:
            sys.exit(0)
        res, t = call("click_ui", {"operationId": "probe-" + uuid.uuid4().hex[:10],
                                   "revision": o["revision"], "element": sys.argv[2]}, rid=3)
        print("click_ui", sys.argv[2], "->", t[:400].replace("\n", " "))
        time.sleep(1)
        state()
    elif cmd == "tool":
        res, t = call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
        print(t[:1200])
