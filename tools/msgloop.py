import json, os, sys, time, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp


def call(name, args=None, rid=2):
    s, _ = mcp.connect()
    res, _ = mcp.call(s, name, args or {}, rid=rid)
    return res, mcp.text_of(res)


def obs():
    res, t = call("observe")
    return json.loads(t)


def click(key):
    o = obs()
    res, t = call("click_ui", {"operationId": "probe-" + uuid.uuid4().hex[:10], "revision": o["revision"], "element": key}, rid=3)
    print("  click", key, "->", t[:90].replace("\n", " "))
    time.sleep(1)


for i in range(6):
    o = obs()
    if o["screen"] != "message":
        print("screen:", o["screen"])
        break
    els = {e.get("asset"): e["key"] for e in o.get("elements", []) if e.get("asset")}
    txt = " ".join((e.get("text") or "") for e in o.get("elements", []))[:80].replace("\n", " ")
    print(i, "message:", txt)
    if "resour82.def" in els:
        click(els["resour82.def"])
    if "iokay.def" in els:
        click(els["iokay.def"])
    else:
        break
