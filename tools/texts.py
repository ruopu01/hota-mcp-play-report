"""Print element texts on the current screen (read-only)."""
import json
import mcp

session, _ = mcp.connect()
res, _ = mcp.call(session, "observe", {})
o = json.loads(mcp.text_of(res))
print("screen:", o.get("screen"), "rev:", o.get("revision"))
for e in (o.get("elements") or []):
    t = (e.get("text") or "").strip()
    if t:
        print("  ", e.get("key"), "|", t[:60], "| sel:", e.get("selected"))
