"""Print the actions available on the current screen (read-only)."""
import json
import mcp

session, _ = mcp.connect()
res, _ = mcp.call(session, "observe", {})
o = json.loads(mcp.text_of(res))
print("screen:", o.get("screen"), "rev:", o.get("revision"))
for a in (o.get("actions") or []):
    if isinstance(a, dict):
        print("  ", a.get("key"), "|", (a.get("label") or "")[:70])
    else:
        print("  ", a)
