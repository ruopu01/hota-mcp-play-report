# tools/ — 我用过的客户端与自动化脚本

全部是 **纯 Python 3（无第三方依赖）**，只做一件事：把 MCP 的 HTTP 接口包成命令行。
它们不读游戏内存、不 hook 进程 —— 只跟 `127.0.0.1:18773/mcp` 说话。

## 客户端

| 文件 | 作用 |
| --- | --- |
| `mcp.py` | 最小 MCP 客户端。`connect()` 拿 session，`call(session, name, args)` 调工具，`text_of(res)` 取文本。支持 `Authorization: Bearer <connection.token>` 与 SSE 解析 |
| `play2.py` | 日常操作壳：`state` / `near` / `act <action>` / `move <x> <y>` / `go <x> <y>` / `endturn` / `click <key>` / `plan <file>` / `tool <name> <json>` |
| `mvt.py` | 直接按坐标走：`python mvt.py 12 8` → `move_to_tile` |
| `endday.py` | 收工例行：`observe` 确认在冒险屏 → `debug_capture` 存 PNG 到 `turnlog/dayNN-W-M.png` → 往 `turnlog/index.md` 追加一行 |
| `msgloop.py` | 对话框清理机：循环点 `iokay.def`，遇 `resour82.def` 先点金币选项，直到离开 `message` 屏 |
| `capture.py` | 调 `debug_capture`，打印落盘路径 |
| `actions.py` / `texts.py` / `eli.py` | 只打印动作表 / 只打印非空文本 / 打印元素的像素矩形（`inspect_element`） |

## 输入模拟（绕 bug 用）

| 文件 | 作用 |
| --- | --- |
| `clickat.py` | 按元素 key 做**像素点击**：`EnumWindows` 找标题含 "Horn of the Abyss" 的窗口，`GetClientRect` 得到 1180×664，按比例缩放后 `PostMessage 0x200 → 0x201 → 0x202` |
| `clickxy.py` | 直接给 (x, y) 点击，同上消息序列 |
| `sendkey.py` / `escape.py` | 发单个按键：`0x0100` keydown / `0x0101` keyup，`lParam = scan<<16\|1`（+ `0xC0000000`）。`escape.py` 固定发 Esc，用来关掉任何卡住的屏 |

> **为什么需要这些**：见 [`../problems/02-兵格与交接.md`](../problems/02-兵格与交接.md)
> 与 [`../problems/03-对话框与按钮.md`](../problems/03-对话框与按钮.md)。
> 语义动作点不到的地方，只能退回"真的按一下键"。

## 自动化

| 文件 | 作用 |
| --- | --- |
| `autoplay.py` | 第一局的挂机脚本：找最近可拾取目标 → `move_to` → 捡 → 没移动力就结束回合。含全部 workaround（stale revision 重试、`used`/`bad` 黑名单、对话框 settle、Esc 兜底） |

## 典型用法

```powershell
$env:PYTHONIOENCODING='utf-8'      # 必须，否则俄语文本在 GBK 控制台上炸
python play2.py state               # 看一眼当前屏
python play2.py go 12 8             # 走到 (12,8)
python play2.py act turn:end        # 结束回合（自带 message:confirm）
python endday.py                    # 收工：截图 + 记账
```

## 客户端坐标缩放

`debug_capture` 给的是 1180×664 的 framebuffer；`clickat.py` 用 `GetClientRect`
拿窗口客户区（本机也是 1180×664，缩放比 1.0），再 `PostMessage`。
如果换分辨率，先把 `scale = min(client_w/width, client_h/height)` 算出来再乘 ——
这跟 hota-mcp 内部 `ToWindow` 的 letterbox 算法一致。
