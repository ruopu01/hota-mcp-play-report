# 让 AI 亲手玩一局《英雄无敌 3》：hota-mcp 实战记录

> 2026-11-02 晚，在一台 Windows 机器上把 [timoncool/hota-mcp](https://github.com/timoncool/hota-mcp)（v1.0.2）接到 GOG 版《HoMM3 Complete + Horn of the Abyss 1.8.1 + HD Mod 5.8》上，实际打完十几回合，并写了自动挂机脚本压测。
>
> 这份仓库是当晚的完整记录：安装过程、真实操作日志、**8 个可复现的问题**、以及我从中看出的设计取舍。

---

## 一句话结论

**它真的能玩。** 全程没有一个真实鼠标点击、没有截图 OCR：AI 通过 MCP 读到结构化的局面（英雄坐标、移动力、资源、城镇、战斗单位），再按语义动作操作游戏（`act town:construction`、`move_to`、`combat:auto`）。

**但它现在还不够稳。** 一条随机地图路径会让全部读屏工具崩掉（`Arithmetic operation resulted in an overflow.`），城镇确认框对合成点击无效，驻军兵种无法交给英雄——最后我连"把兵带出城"都做不到，挂机只能原地捡资源。

---

## 1. 装了什么

| 组件 | 版本 / 来源 | 说明 |
| --- | --- | --- |
| 游戏本体 | GOG《Heroes of Might and Magic 3 Complete》 | `setup_homm_3_complete.exe`，装完约 1.0 GB 数据 |
| HotA | 1.8.1（官方安装器，347 MB） | `HotA.dll` 2026-11-02，`h3hota.exe` 时间戳仍是 2023（版本在 DLL 里，exe 不重建） |
| HD Mod | 5.8 R22 | `HD_Launcher.exe` 5.7.0.7 / `HD_LauncherNative.dll` 5.5.0.0 / `HD_HOTA.dll` 5.0.0.5 |
| hota-mcp | 1.0.2（34.4 MB 安装包） | 装到 `D:\Heroes3\HotaMcp`，服务监听 `127.0.0.1:18773/mcp` |

安装要点（踩过的坑）：

- 安装器会挑 `HKCU\Software\HotaMcp\GameDir`、GOG 注册表键或几个固定路径做游戏目录；**非标准目录必须先写注册表**，否则静默安装直接 `exit 2`（`Abort "Папка игры не найдена"`）。
- 它要求游戏目录里同时有 `h3hota HD.exe`、`HotA.dll`、`HD_Launcher.exe`——装 HotA 但没装 HD Mod 的目录不算数。
- 服务裸跑（`HotaMcp.exe`）即可提供 HTTP MCP；`--launch` 那条链会自己起 HD Launcher，但需要它托管才能用 `start_game`。

## 2. 它是怎么工作的（读源码 + 实测）

```
MCP 客户端 (Claude/DSH/任意)  ──HTTP+SSE──▶  HotaMcp.exe (C#/.NET, 127.0.0.1:18773)
                                                │  只读 OpenProcess + ReadProcessMemory
                                                │  绝对地址读全局状态（0x6992d0 管理器、0x699538 主结构）
                                                ▼
                                          注入的 native bridge (C++, 游戏进程内)
                                                │  PostMessage 0x200/0x201/0x202 合成鼠标
                                                ▼
                                            游戏窗口（真实按钮）
```

- **观察**：不截图、不 OCR。直接按固定绝对地址读内存里的玩家记录、英雄数组、城镇、控件链表，把"当前屏幕"识别成 `adventure` / `town` / `combat` / `popup_choice` 等，再翻译成 JSON。
- **幂等**：每次状态都带 `revision`（状态哈希）。动作必须带 `operationId` + `revision`；revision 过期就拒绝（`[STALE_REVISION]`），同一 operationId 重复提交直接返回上次结果，避免"英雄走两步"。
- **确认**：动作发出后不信任自己的点击，而是轮询读屏，等"屏幕变了"或"某个数值变了"才算完成；超时则标记 `uncertain`（不确定，禁止换 id 重试）。
- **知识**：内置 1.6 MB 文档 + SQLite FTS5 检索（`hota_docs`），以及一份给 agent 的 `SKILL.md` 回合循环。

## 3. 今晚做了什么

1. **17:46** 起服务，接上游戏 → `game_status` 返回 `attached`，五项结构自检全过，`build.status: compatible`。
2. **17:52** 手动走完开局：`menu:new` → `menu:single` → 选图 **Air Supremacy**（72×72，3 人）→ 高级选项里把红色玩家的城镇用 `:город:вперёд/:назад` 转回 **Замок（城堡）** → `scenario:difficulty:1`（最低，Пешка 80%）→ `scenario:start`。
3. **17:58–18:30** 实际游玩 + 自动挂机，共 **1083 次 MCP 调用**，把一局从第 1 天推进到第 7 周（约 43 个游戏日）。
4. **18:30** 叫停（挂机陷入原地循环，见下）。

### 实测数据（`logs/usage-sample.jsonl` 汇总）

| 指标 | 数值 |
| --- | --- |
| MCP 调用 | 1,083 次（observe 599 / nearby 199 / click 173 / move 100 / capture 6 / plan 3 / inspect 2 / attack 1） |
| 工具总耗时 | 922 秒（平均 **852 ms/次**） |
| 回传上下文 | **10.69 MB**（平均 10 KB/次） |
| 被拒绝 | 50 次：`NO_PATH` 23、`UNKNOWN_CONTROL` 10、`WRONG_SCREEN` 9、`STALE_REVISION` 5、`NO_HERO_ON_MAP` 2、`STALE_TARGETS` 1 |

> 一个游戏日 ≈ 6–20 秒真实时间。慢的不是 AI，是每次动作后的"确认轮询"。

### 战果

- 英雄 **Oidana**（要塞，狗头人 + 公羊 + 雪精灵），城镇 **Anabar**。
- 建了猛犸厩、市场，招了 4 只猛犸（进了驻军）、招满三级兵。
- 吃掉的宝箱/风车/花园/幸运泉/矿泉：金币 30.9k → **约 67k**，知识 +1。
- 打掉挡路的 **Rogue×31**（自动战斗）：胜利 +310 经验，损失 9 狗头人 + 7 公羊。
- 结局：卡在"兵力带不出城"，只能无限捡资源。**没有分出胜负**。

## 4. 踩到的问题（8 个，全部可复现）

| # | 现象 | 严重度 |
| --- | --- | --- |
| 1 | 随机地图 + Tournament Rules 弹窗确认后，**所有读屏工具**永久返回 `Arithmetic operation resulted in an overflow.`（固定图不发生；重启游戏可复现） | 🔴 致命 |
| 2 | 建造/购买的**确认框对合成鼠标点击无效**：`building:buy`/`building:cancel` 返回 `uncertain`，`click_ui` 被拒 `[UNKNOWN_CONTROL] Use an available semantic action`；用真实键盘 Enter 才生效 | 🔴 高 |
| 3 | **驻军兵种无法交给英雄**：`town:lead` → `Town garrison row control not found in the town dialog`；`army:take:X` → `Клетка N верхнего ряда не найдена на экране города` | 🔴 高 |
| 4 | `scenario_info` 屏的退出按钮（`gspexit.def`）点了被拒，只能用 Esc | 🟠 中 |
| 5 | 随机地图高级选项：`setup:<颜色>:город:<城名>` 的候选被 "Player Turn Duration: Classic" 污染（`Игра предлагает: 00:00 + 00:00 + 00:00`），只能用 `:вперёд/:назад` 转 | 🟠 中 |
| 6 | 路线缓存 stale 时 `nearby_targets` 全部 `not_available`；同一目标两次调用间状态会翻转，`move_to` 有时又能走 | 🟠 中 |
| 7 | 多个一次性动作实际生效却返回 `uncertain`（`scenario:difficulty`、宝箱选项、建造确认） | 🟡 低 |
| 8 | 连续 6 次观察无变化时 brief 出现 `Топтание: 6 наблюдений подряд без единого изменения`（设计如此，但会让 agent 误判） | 🟡 低 |

详细复现步骤与原始错误文本见 [`docs/bugs.md`](docs/bugs.md)。

## 5. 我怎么评价它

**做得好的地方**

- **协议设计**：`revision` + `operationId` + 独立"确认"证据，是给 LLM 用的接口里少见的严谨做法——它把"我点了吗？"这个问题从"信任工具返回值"变成了"再读一次世界"。
- **错误码是给模型看的**：17 个 `[CODE]` 不是给程序 catch 的，是给模型纠错的（"Revision 过期，重新观察" / "这条路被守卫封了，先打或绕"）。实测 agent 确实能靠这些码自我恢复。
- **零 OCR**：读内存 + 结构签名（而不是文件哈希），HD Mod/HotA 更新不会让它失效，只要求"结构在正确的位置"。
- **文档层**：1.6 MB 的 FTS5 知识库让"规则问答"不必进上下文。

**局限**

- **脆弱**：一个未处理的 `OverflowException` 就能让整局游戏不可观测，且没有降级路径（不退回 OCR/截图）。
- **覆盖面**：31 个工具里，"建设/招募/交接"这条最常用的链路坏掉了；`hotseat`、`lan` 在 `capabilities.unavailable` 里明说没做。
- **速度**：852 ms/次的确认轮询决定了它更像"看一步走一步"，而不是拟人操作。

## 6. 想自己复现

```powershell
# 1) 装游戏（GOG Complete）+ HotA 1.8.1 + HD Mod 5.8
# 2) 写游戏目录（非标准路径必做）
reg add "HKCU\Software\HotaMcp" /v GameDir /t REG_SZ /d "D:\...\Heroes of Might and Magic 3 Complete" /f
# 3) 静默安装 MCP
HotaMcp-Setup-1.0.2.exe /S /D=D:\Heroes3\HotaMcp
# 4) 起服务 + 起游戏
Start-Process D:\Heroes3\HotaMcp\app\HotaMcp.exe -WindowStyle Hidden
Start-Process ".\h3hota HD.exe" -WorkingDirectory <游戏目录>
# 5) 用任意 MCP 客户端连 http://127.0.0.1:18773/mcp（Bearer token 见 %LOCALAPPDATA%\HotaMcp\connection.token）
```

`tools/mcp.py` 是一个零依赖的 MCP 客户端（HTTP+SSE），`tools/autoplay.py` 是当晚的挂机脚本（含全部 workaround）。

## 7. 文件说明

```
README.md                     本文
docs/bugs.md                  8 个问题的复现步骤与原始错误
docs/architecture.md          项目结构与协议设计笔记（读源码所得）
docs/timeline.md              当晚时间线（含每次关键调用）
screenshots/                  游戏内截图（adventure / 战后）
logs/journal-tail.jsonl       MCP 会话日志尾部（operation_started/completed）
logs/usage-sample.jsonl       调用用量（延迟、字节数、拒绝码）样本
tools/                        MCP 客户端、挂机脚本、截图脚本
```

## 8. 声明

- 本项目仅为个人实验记录，与 `timoncool/hota-mcp` 作者无关；`hota-mcp` 本身的许可证见其仓库。
- 游戏素材（截图）版权归 Ubisoft / HotA 团队所有，仅作技术说明用途。
- 未修改游戏的任何文件；`tools/` 里的脚本只通过 MCP 接口操作游戏。
