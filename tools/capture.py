import base64, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp

s, _ = mcp.connect()
res, _ = mcp.call(s, "debug_capture", {}, rid=9)
r = (res or {}).get("result", {})
print("isError:", r.get("isError"))
for c in r.get("content", []):
    t = c.get("type")
    if t == "image":
        data = base64.b64decode(c["data"])
        out = os.path.join(os.environ["TEMP"], "hotamcp", "game_capture.png")
        open(out, "wb").write(data)
        print("image saved:", out, len(data), "mime:", c.get("mimeType"))
    else:
        print(t, str(c.get("text"))[:400])
