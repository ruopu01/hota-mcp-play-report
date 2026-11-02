import json, os, sys, urllib.request, urllib.error

URL = "http://127.0.0.1:18773/mcp"
DATA = os.path.join(os.environ["LOCALAPPDATA"], "HotaMcp")
TOKEN = open(os.path.join(DATA, "connection.token"), "r", encoding="utf-8").read().strip()


def parse(body: str):
    body = body.strip()
    if not body:
        return None
    if body.startswith("{"):
        return json.loads(body)
    out = []
    for line in body.splitlines():
        if line.startswith("data:"):
            chunk = line[5:].strip()
            if chunk and chunk != "[DONE]":
                out.append(json.loads(chunk))
    return out[-1] if out else None


def post(payload, session=None, notify=False):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("Authorization", "Bearer " + TOKEN)
    if session:
        req.add_header("Mcp-Session-Id", session)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read().decode("utf-8", "replace")
            hdrs = dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        hdrs = dict(e.headers)
    if notify:
        return None, hdrs, body
    return parse(body), hdrs, body


def connect():
    res, hdrs, _ = post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "probe", "version": "1.0"}},
    })
    session = hdrs.get("Mcp-Session-Id") or hdrs.get("mcp-session-id")
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session, notify=True)
    return session, res


def call(session, name, args=None, rid=2):
    res, _, raw = post({
        "jsonrpc": "2.0", "id": rid, "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    }, session)
    return res, raw


def text_of(res):
    if not res:
        return ""
    if "error" in res:
        return "ERROR " + json.dumps(res["error"], ensure_ascii=False)
    parts = res.get("result", {}).get("content") or []
    return "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")


if __name__ == "__main__":
    session, init = connect()
    print("session:", session)
    print("server:", json.dumps(init.get("result", {}).get("serverInfo", {}), ensure_ascii=False))
    name = sys.argv[1] if len(sys.argv) > 1 else "game_status"
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    res, raw = call(session, name, args)
    print("isError:", res.get("result", {}).get("isError") if res else "?")
    print(text_of(res)[:4000])
