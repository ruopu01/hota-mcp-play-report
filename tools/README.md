# 脚本说明

这些脚本都是"通过 MCP 接口操作游戏"的客户端，不读写游戏内存，也不修改游戏文件。

| 文件 | 作用 |
| --- | --- |
| `mcp.py` | 零依赖 MCP 客户端：读 `%LOCALAPPDATA%\HotaMcp\connection.token`，走 Streamable HTTP + SSE，暴露 `call(name, args)` 与 `schemas()` |
| `autoplay.py` | 当晚的挂机循环：settle 对话框 → 挑最近的可拾取目标 → `move_to` → `turn:end`，含全部 workaround（Esc/Enter 合成键盘、revision 重试、visited 去重） |
| `play2.py` | 手动单步工具：`state` / `near` / `act <action>` / `move <x> <y>` / `go <x> <y>` / `endturn` / `click <key>` / `plan <file>` / `tool <name> <json>` |
| `capture.py` | 调 `debug_capture` 拉一张游戏 framebuffer PNG 并打印落盘路径 |
| `msgloop.py` | 循环点掉 message 屏（开局信、宝箱、事件通知），遇到金币选项优先选金币 |

## 用法

```powershell
$env:PYTHONIOENCODING = 'utf-8'   # 必须：界面文本是俄语，默认 GBK 会乱码
& 'C:\Program Files\Python314\python.exe' .\autoplay.py
```

前置条件：

1. `HotaMcp.exe` 服务在跑（`127.0.0.1:18773`）；
2. 游戏已启动并 `game_status` 返回 `attached`；
3. 游戏窗口标题含 "Horn of the Abyss"（脚本用 `EnumWindows` 找窗口发键盘消息）。

## 已知限制

- `autoplay.py` 只会"捡资源 + 结束回合"——因为驻军兵种交接在本 build 不可用（见 `docs/bugs.md` #3），它无法壮大军队，也就赢不了。
- 建造/招募的确认框必须用真实键盘 Enter 触发（见 `docs/bugs.md` #2）。
- 随机地图会在开局后让所有读工具崩掉（见 `docs/bugs.md` #1），脚本对此没有恢复手段。
