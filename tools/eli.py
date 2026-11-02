import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp

key = sys.argv[1]
s, _ = mcp.connect()
res, _ = mcp.call(s, "observe", {}, rid=2)
obs = json.loads(mcp.text_of(res))
rev = obs["revision"]
res, _ = mcp.call(s, "inspect_element", {"element": key, "revision": rev}, rid=3)
print(mcp.text_of(res))
