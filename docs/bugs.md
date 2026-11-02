# 复现记录：hota-mcp 1.0.2 在 HotA 1.8.1 + HD Mod 5.8 上的 8 个问题

环境：Windows / GOG HoMM3 Complete / HotA 1.8.1 / HD Mod 5.8 R22 / hota-mcp 1.0.2（`game_status` → `build.status: compatible`，五项结构自检全部通过，`attach` 正常）。

所有错误文本均从 MCP 返回原文抄录（部分是俄语，游戏界面语言为俄语）。

---

## 1. 🔴 随机地图 + Tournament Rules 弹窗后，读屏永久溢出

**步骤**

1. `observe` → `main_menu`
2. `act menu:new` → `game_type`
3. `act menu:single` → `scenario_selection`（此时无异常）
4. `act scenario:random` → 切到随机地图面板
5. `act rmg:teams:2`、`setup:size:36` 等设置
6. `act scenario:start` → `popup_choice`（Tournament Rules 复选框）
7. `act popup:подтвердить`

**期望**：进入 adventure 屏。
**实际**：工具返回纯文本

```
Arithmetic operation resulted in an overflow.
```

此后**所有**读状态工具（`observe`、`nearby_targets`、`debug_snapshot`、`debug_capture`、`read_map`）都返回同一句，持续 10+ 次轮询不恢复。

**旁证**

- 同一时刻 `game_status` 仍返回 `state: attached`、`build.status: compatible`、五项检查全过 → 桥接和结构定位本身没坏，是读状态时代码里抛了 `OverflowException`。
- 屏幕截图确认游戏**已经进入冒险地图**（窗口标题 "Heroes of Might and Magic III: Horn of the Abyss"，右侧英雄栏、迷你地图都在）。所以不是"游戏卡住"，是 adapter 崩了。
- **重启游戏后走默认固定图 Air Supremacy 全程正常**（35 个游戏日、1083 次调用未复现）。因此触发条件与"随机地图"这条路径相关，最可能是读取随机地图尺寸/坐标时把某个 16 位值当有符号数（36 尺寸、或地图边缘坐标 0/负偏移）→ 溢出。
- 崩溃后没有降级：不会退回截图/OCR，也不会提示"请重开本局"，整局不可观测。

**影响**：随机地图是 HoMM3 最常用的开局方式之一，这条路径等于"随机图不可玩"。

---

## 2. 🔴 建造/招募确认框对合成鼠标点击无效

**步骤**

1. 进城：`act town:enter`（或 `move_to` 进城）→ screen `town`
2. `act town:construction` → 建造列表
3. `act building:inspect:5`（猛犸厩）→ **弹出确认框**
4. `act building:buy`

**期望**：扣资源、建筑建成。
**实际**：

```
{"status":"uncertain","message":"Dispatch started; do not repeat using a new ID."}
```

资源与建筑数都没变。换 `act building:cancel` 同样 `uncertain`。改用 `click_ui {"element":"ui:8"}`（确认按钮）：

```
[UNKNOWN_CONTROL] Use an available semantic action
```

**可用绕过**：用真实键盘消息打确认框

```powershell
# PostMessage(hwnd, 0x0100, 0x0D, 0x001C0001)  # WM_KEYDOWN VK_RETURN
# PostMessage(hwnd, 0x0101, 0x0D, 0xC01C0001)  # WM_KEYUP
```

发完建筑立刻建成（已验证：猛犸厩 15 木 + 4000 金、市场 5 木 + 500 金）。说明确认框是标准的 Windows 对话框，walk 不到 `ScreenActions` 的控制树里。

招募同理：`recruit:max` / `recruit:buy` 卡在同一处，用 Enter 绕过。

---

## 3. 🔴 驻军兵种无法交给英雄

**步骤**

1. 城里招兵（`town:recruit:2` → `recruit:max` → `recruit:buy` + Enter）→ 兵进入**驻军**，英雄队伍不变
2. 尝试合兵：`act town:lead`
3. 或直接取：`act army:take:Mammoth`

**实际**

```
Town garrison row control not found in the town dialog
```

```
Клетка 3 верхнего ряда не найдена на экране города
```

（`army:take:Snow Elf` / `Kobold` / `Mountain Ram` 分别报"第 0/1/2 格找不到"。）

**影响**：这是最要命的——招来的兵（4 只猛犸、15 狗头人、9 公羊、7 雪精灵）全部锁在城里，英雄只剩 14 狗头人 + 4 雪精灵。**兵力无法增长 → 无法推进地图 → 挂机只能捡资源**。

---

## 4. 🟠 `scenario_info` 屏退出按钮无效

`act game:scenario_info` 打开信息屏（能正确显示难度 80%），但：

- `click_ui {"element":"ui:23"}`（`gspexit.def`）→ `[UNKNOWN_CONTROL] Use an available semantic action`
- 没有任何 `act` 形如 `scenario_info:exit`

只能发 Esc（`WM_KEYDOWN 0x1B`, `lParam 0x00010001`）退出。

---

## 5. 🟠 随机地图高级选项：颜色→城镇 的候选被文本框污染

`act scenario:players` 进入高级选项后：

```
act setup:красный:город:Замок
→ «Замок» не предлагается в столбце «город» у цвета «красный».
  Игра предлагает: 00:00 + 00:00 + 00:00
```

`00:00 + 00:00 + 00:00` 是同一屏上 "Player Turn Duration: Classic" 那个计时器文本被当成了"可选城镇列表"。

**绕过**：`setup:красный:город:вперёд` → Оплот，`:город:назад` → 回到 Замок（两步都 completed，说明箭头路径正常，只是候选集提取错了）。

---

## 6. 🟠 路线缓存 stale 与状态翻转

```
nearby_targets → 所有目标 route.state = "not_available"
detail: "The game's route cache is stale: it was built for 2360 movement points
         while the hero now has 1500"
```

再调一次 `nearby_targets` 立刻恢复 `reachable_today`。

另有反向情况：`route.state = "not_available"` 的宝箱，`move_to` 有时仍会走（返回 "Hero stopped short of the target"），有时 `[NO_PATH] … клетка отрезана препятствием`。两次调用之间状态会翻转，agent 很难判断"该不该试"。

---

## 7. 🟡 动作实际生效但返回 `uncertain`

- `scenario:difficulty:1` → `uncertain`，但事后读 `setup.difficulty` 已是 `Пешка (80% очков)`
- 宝箱选金币 → `uncertain`，金币确实 +900
- 建造确认 → `uncertain`，但用 Enter 后生效（见问题 2，属于同一根因）

`uncertain` 的语义是"不确定"，可实际上服务端往往知道结果，只是确认条件没满足（例如屏幕没变但数值变了）。

---

## 8. 🟡 `Топтание` 提示会让 agent 误判

连续 6 次 `observe` 无变化时，brief 里出现：

```
Топтание: 6 наблюдений подряд без единого изменения
```

设计意图是提醒"你在原地打转"，但在"等待 AI 回合"场景下（合法地连点多次 `observe`），这句话会被模型理解成"我卡住了"，从而触发不必要的动作序列。

---

## 附：拒绝码统计（当晚 1083 次调用）

| 代码 | 次数 | 典型原因 |
| --- | --- | --- |
| `NO_PATH` | 23 | 目标被守卫/河流挡住；路线缓存过期 |
| `UNKNOWN_CONTROL` | 10 | 确认框按钮、`gspexit.def` 不在语义动作表里 |
| `WRONG_SCREEN` | 9 | 对话框没关就发动作 |
| `STALE_REVISION` | 5 | `nearby_targets` 刷新了状态，动作前没重新 observe |
| `NO_HERO_ON_MAP` | 2 | 英雄在城里/过场 |
| `STALE_TARGETS` | 1 | 目标列表变化 |

这些码本身是**好设计**：当晚的自动脚本正是靠它们逐条自我修正的。问题不在码，而在"该有的语义动作根本没实现"（问题 2、3）。
