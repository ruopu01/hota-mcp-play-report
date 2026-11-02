import base64, json, os, sys, uuid
import mcp

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "turnlog")
os.makedirs(LOG, exist_ok=True)
s, _ = mcp.connect()


def observe():
    res, _ = mcp.call(s, "observe", {})
    return json.loads(mcp.text_of(res))


o = observe()
if o.get("screen") != "adventure":
    print("not on adventure:", o.get("screen"))
    sys.exit(0)
d = o.get("date") or [0, 0, 0]
res, _ = mcp.call(s, "debug_capture", {}, rid=9)
r = (res or {}).get("result", {})
data = None
path = None
for c in r.get("content", []):
    if c.get("type") == "image":
        data = base64.b64decode(c["data"])
    elif c.get("type") == "text":
        try:
            path = json.loads(c["text"]).get("path")
        except Exception:
            pass
if data is None and path and os.path.exists(path):
    data = open(path, "rb").read()
name = "day%02d-%d-%d.png" % (d[0], d[1], d[2])
dst = os.path.join(LOG, name)
if data:
    open(dst, "wb").write(data)
    h = o.get("hero") or {}
    line = "- day %d/%d/%d hero=%s pos=%s mp=%s/%s gold=%s shot=%s" % (
        d[0], d[1], d[2], h.get("name"), h.get("position"), h.get("movement"),
        h.get("maxMovement"), (o.get("resources") or [0]*7)[6], name)
    open(os.path.join(LOG, "index.md"), "a", encoding="utf-8").write(line + "\n")
    print("shot:", name, len(data), "bytes")
    print(line)
else:
    print("capture failed")
