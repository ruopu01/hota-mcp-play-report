import json, sys, mcp, uuid
s, _ = mcp.connect()
res, _ = mcp.call(s, "observe", {})
o = json.loads(mcp.text_of(res))
x, y = int(sys.argv[1]), int(sys.argv[2])
z = int(sys.argv[3]) if len(sys.argv) > 3 else 0
res, raw = mcp.call(s, "move_to_tile", {"operationId": "probe-" + uuid.uuid4().hex[:10],
                                        "revision": o["revision"], "x": x, "y": y, "z": z})
print(mcp.text_of(res)[:800])
