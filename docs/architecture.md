# 架构笔记：hota-mcp 是怎么让 agent "看见"并"操作"一个 2000 年前的游戏

> 基于 v1.0.2 源码（C# + 少量 C++）与实机运行观察整理。

## 1. 为什么不能用截图 + OCR

作者的选择很明确：**不截图、不 OCR、不猜像素**。

- 游戏是 32 位老程序，内存布局稳定，可以直接 `ReadProcessMemory`。
- 视觉方案在 HoMM3 里很脆：分辨率可变、HD Mod 会缩放、字体渲染毫秒级变化、兵种美术相似。
- 读内存拿到的是**语义**（"第 3 格是 4 只猛犸"），不是像素，agent 不需要"看图理解"。

代价：**与具体 build 强绑定**。所以它用"结构签名 + 自检"来兜底（见 §4）。

## 2. 分层

```
src/HotaMcp/
  Program.cs          MCP 主机、HTTP/stdio、Token、审计
  GameTools.cs        31 个 [McpServerTool]（模型可见的接口）
  Bridge.cs           编排：读-算-写、幂等账本、确认轮询
  GameReader.cs       读状态：屏幕、英雄、城镇、资源、地图
  GameCommands.cs     语义动作 → 具体按键/点击（Route/Key/Slot 表）
  ScreenActions.cs    每个界面的合法动作清单（popup_choice/town/combat/...）
  ScreenBriefing.cs   给模型看的自然语言摘要
  MapReader/CombatReader/TownReader/RouteReader.cs   各屏专用解析
  GameReference.cs    HotA 数据表（兵种/建筑/宝物）
  DocsIndex.cs        FTS5 文档检索（1.6 MB 知识库）
  Refusals.cs         17 个拒绝码 + 错误过滤器
native/game/          注入游戏的 bridge（C++）
docs/knowledge/       官方文档、规则、play 指南
skills/hota-player/SKILL.md   给 agent 的回合循环手册
```

## 3. 三个关键设计

### 3.1 revision：状态是一个带版本号的快照

每次 `observe` 返回的 JSON 里都有 `revision`（状态哈希）。所有写动作必须带上它：

- 服务端比对 revision，不一致就 `[STALE_REVISION]` 拒绝 —— "你看到的不是现在的世界，重看"。
- 这把"读-改-写"竞态从模型手里拿走了：模型不需要自己维护"我读的是什么时候的状态"。

### 3.2 operationId：动作是幂等的

同一个 `operationId` 重复提交返回第一次的结果，不会执行两次。

- 网络重试、agent 幻觉重发都不会造成"英雄多走一步"。
- 超时则返回 `uncertain`（"我不知道有没有生效"），并禁止换 id 重试——宁可停，不可重复。

### 3.3 独立证据：不要相信自己的点击

动作发出后，Bridge 会轮询读屏，检查**与点击无关的证据**：

- 屏幕变了（`screen transition confirmed by revision change`）
- 或某个数值变了（`same screen, state change confirmed by revision`）
- 都不满足 → `uncertain`

这让"我以为我点了"和"游戏真的响应了"分开。

## 4. 结构自检（对付"更新后失效"）

启动/接入时跑五项检查，任何一项失败 → `build.status: incompatible`，并说明缺什么：

| 检查 | 依据 |
| --- | --- |
| window manager | `0x6992d0` 指针 → `+0x54` 对话框 → vtable 落在 `0x400000..0x700000` |
| surface geometry | `manager+0x40` → 宽/高（640..8192 / 480..8192） |
| hero array | `0x4317e1` 处 19 字节机器码签名 `8BC2C1E00603C28D04C08D8441` |
| town entry | `0x4081bd` 两字节 == `0x8b82`，`0x4081bf` 为偏移 |
| manager list | `0x699550` |

实测：正确的 HotA 1.8.1 + HD Mod 5.8 输出

```
window manager   active dialog class 0x63ff60
surface geometry 1180x664
hero array       record stride 0x492, offset 0xfdbd0000
town entry       town array offset 0x21614
manager list     2 managers
```

而"HotA 数据 + 旧 HD Mod 5.2"的整合包则报 `manager pointer is not a pointer; Invalid game layout` —— 自检确实拦住了不兼容组合，而不是静默返回垃圾数据。

## 5. 读屏细节（实测可见的字段）

`observe` 返回的骨架：

```json
{ "revision": "...", "player": 0, "date": [day, week, month],
  "resources": {"wood":0,"mercury":0,"ore":0,"sulfur":0,"crystal":0,"gems":0,"gold":0},
  "hero": {"id":199,"name":"Oidana","position":[66,37,0],"movement":1500,"maxMovement":1500,
           "primary":[0,4,1,2],"army":["Kobold x14","Snow Elf x4"],"plannedDestination":[]},
  "towns": [{"name":"Anabar","built":10,"garrison":["Mammoth x4", ...],"recruitable":[[...]]}],
  "screen": "adventure", "elements": [...], "actions": ["move:...","town:enter","turn:end"],
  "brief": "自然语言摘要", "side": {...} }
```

- `elements` 是当前屏上可点的控件（`{key:"ui:N", id:224, asset:"iokay.def", text:"...", selected:true}`）。
- `actions` 是**语义动作**，不是控件：`town:construction`、`building:inspect:5`、`building:buy`、`combat:auto`、`move_to`…
- 战斗屏的 `combat.stacks[]` 信息量极大（速度/攻防/血量/伤害/士气/幸运/能力/效果），足够做战术决策。

## 6. 已知没做的

`game_status.capabilities.unavailable` 明确列出：`full_map_coverage`（只能看到视野内）、`hotseat`、`lan`、`full_scenario_setup`、`cost_measurement`。

实际体感还要加两条（本次实测）：随机地图路径会崩（`docs/bugs.md` #1）、城镇兵员交接没有实现（#3）。
