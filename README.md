# 让 AI 亲手玩《英雄无敌 3》：hota-mcp 实战记录

> 2026-11-02，在一台 Windows 机器上把 [timoncool/hota-mcp](https://github.com/timoncool/hota-mcp)（v1.0.2）
> 接到 GOG 版《HoMM3 Complete + Horn of the Abyss 1.8.1 + HD Mod 5.8 R22》上，
> 连打两局、写了自动挂机脚本压测，最后把第二局存档收工。
>
> 全程 **没有一个真实鼠标点击，没有一次截图 OCR**：所有操作都通过 MCP 的 31 个工具完成。
>
> 本仓库是最初 `hota-mcp-play-report`（第一局）与后来 `hota-fat-fish`（第二局）两份记录的合并版，旧仓库已删除。

本仓库两件事分开写：

- 👉 **[`problems/`](problems/)** —— 撞到的 **12 个问题**，每个都有现象、复现步骤、原始报错、绕法
- 👉 **[`diary/`](diary/)** —— 两局的**战报/日记**，逐日记录思路、决策与具体调用（配截图）

---

## 一、用了什么

| 组件 | 版本 / 来源 | 备注 |
| --- | --- | --- |
| 游戏本体 | GOG《Heroes of Might and Magic III Complete》 | `setup_homm_3_complete.exe` |
| HotA | **1.8.1**（官方安装器 347 MB，Inno Setup） | `HotA.dll` 是新的，`h3hota.exe` 时间戳仍是 2023——版本在 DLL 里 |
| HD Mod | **5.8 R22**（19 MB，Inno Setup） | `HD_Launcher.exe` 5.7.0.7 / `HD_HOTA.dll` 5.0.0.5 |
| hota-mcp | **1.0.2**（34.4 MB，NSIS） | 装到 `D:\Heroes3\HotaMcp`，服务 `127.0.0.1:18773/mcp` |
| 客户端 | 自写的零依赖 Python 客户端 | [`tools/mcp.py`](tools/mcp.py)，HTTP + SSE |

### 它是怎么工作的

```
MCP 客户端 (任意)  ──HTTP+SSE──▶  HotaMcp.exe (C#/.NET, 127.0.0.1:18773)
                                   │  OpenProcess + ReadProcessMemory（只读）
                                   │  按固定绝对址读：管理器 0x6992d0、主结构 0x699538、
                                   │  英雄数组 stride 0x492、城镇数组 …
                                   ▼
                              注入的 native bridge（C++，游戏进程内）
                                   │  PostMessage 0x200/0x201/0x202 合成鼠标事件
                                   ▼
                                游戏窗口（按真实按钮）
```

- **观察**：不截图、不 OCR。直接读内存里的玩家记录、英雄数组、城镇、控件链表，
  把"当前屏幕"识别成 `adventure` / `town` / `combat` / `popup_choice` … 再翻译成 JSON。
- **幂等**：每次状态带 `revision`（状态哈希）。动作必须带 `operationId` + `revision`；
  revision 过期 → `[STALE_REVISION]`；同一 operationId 重复提交 → 直接返回上次结果（防"英雄走两步"）。
- **确认**：发完动作不信任自己的点击，而是**再读一次世界**，等屏幕或数值变化才算完成；
  超时标 `uncertain`（不确定，禁止换新 id 重试）。
- **知识**：内置 1.6 MB 文档 + SQLite FTS5（`hota_docs`），以及给 agent 的 `SKILL.md` 回合循环。

> `game_status` 成功时是这样，五项结构自检全过才允许操作：
>
> ```
> state: attached   build.status: compatible
> "Every structure this adapter uses was found in place"
>   window manager   active dialog class 0x63ff60
>   surface geometry 1180x664
>   hero array       record stride 0x492, offset 0xfdbd0000
>   town entry       town array offset 0x21614
>   manager list     2 managers
> ```

---

## 二、做了什么

两局，一条时间线：

| | 第一局 | 第二局 |
| --- | --- | --- |
| 地图 | Air Supremacy 72×72，3 人 | 随机图 36×36，双层，模板 `2SM2I` |
| 难度 | Эксперт 160% → Нормальный 100% | **Пешка 80%（最低）** |
| 英雄 | Oidana（狗头人/公羊/雪精灵），城 Anabar | Adelaide（Cleric），城 Armitage |
| 方式 | 我自由发挥 + 挂机脚本压测 | 用户在一旁"一步一停"教学 |
| 跨度 | 35 个游戏日 | 10 个游戏日（第 1 周 7 天 + 第 2 周 3 天） |
| 结局 | 卡在"兵带不出城"，被叫停 | 手动打完战斗、把兵运到前线，**存档收工** |

### 数据（两局合计）

| 指标 | 第一局 | 第二局 |
| --- | --- | --- |
| MCP 调用 | 1,083 | 1,454 |
| 总耗时 | 922 s（852 ms/次） | 585 s（403 ms/次） |
| 回传大小 | 10.69 MB | 13.74 MB |
| 拒绝次数 | 50 | 93 |
| 平均一个游戏日 | 6–20 s | 6–20 s |

第二局的拒绝码分布（`data/usage-game2.jsonl`）：

```
STALE_REVISION   42   ← 看完忘重取 revision
WRONG_SCREEN     16   ← 在错误屏幕上按动作
NO_PATH          15   ← 路被挡 / 地下寻路谎报
UNKNOWN_CONTROL  11   ← 对话框按钮不吃语义动作
NO_HERO_ON_MAP    6   ← 忘了先选英雄
MELEE_UNREACHABLE 2
STALE_TARGETS     1
```

---

## 三、结果怎么样

**结论：它真的能玩，但离"稳定可玩"还差一段。**

能做的（全部实测过）：

- 开随机图、调难度、选城、开局；
- 走路（`move_to` / `move_to_tile` / 地下 `hero:step`）、捡资源、访问建筑、占矿；
- 建设（含升级建筑）、招募（含升级兵种）、双英雄交换合兵、酒馆招英雄；
- 战斗：自动战斗 + **手动逐轮指挥**（移动/攻击/等待/防御，含反击与等待节奏）；
- 存档 / 读档 / 回主菜单 / 退出。

第二局终局盘面（Month 1 / Week 2 / Day 3，存档 `fish-10.GM1`）：

```
Adelaide  (8,3,1)  mp 1560   Pikeman 39 / Marksman 32 / Griffin 12 / Steel Elf 7 / Swordsman 3 / Halberdier 32
           Cleric lvl 3, 四维 1/0/2/5, 魔 32, Expert Wisdom + Basic Water Magic + Frost Ring
Cuthbert  (13,2,1) mp 1700   Marksman 1（押运工）
Rion      (15,0)   mp 1560   Pikeman 1（探路工）
Armitage  built 7            Castle / Town Hall / Upg. Guardhouse / Upg. Archers' Tower / Tavern / Mage Guild 1
资源      木 38 / 汞 18 / 矿 10 / 硫 15 / 晶 15 / 宝 15 / 金 12,900
```

做不到 / 很痛的：

- 随机图某条路径会让**全部读屏工具崩掉**（`Arithmetic operation resulted in an overflow.`）；
- 城镇里的**兵格语义动作全灭**（`army:give/take/open/split`、`town:lead`、`hero:out`），
  只能靠"双击兵格像素 + 语义升级"绕过；
- 对话框按钮经常不吃语义点击，得退回键盘 Enter / Esc；
- `menu:load` 是坏的，真存档列表藏在 `menu:single` 后面；
- 地下寻路经常谎报 `NO_PATH`，只能一格一格 `hero:step`。

---

## 四、过程里遇到的问题（速览）

12 条，全部在 [`problems/`](problems/) 里有复现步骤与原始报错。

| # | 问题 | 严重度 | 详见 |
| --- | --- | --- | --- |
| 1 | 随机图 + Tournament Rules 弹窗后，所有读屏工具永久溢出 | 🔴 致命 | [problems](problems/01-读屏崩溃.md) |
| 2 | 兵格类动作全部失效（兵出不了城 / 交不到英雄手上） | 🔴 高 | [problems](problems/02-兵格与交接.md) |
| 3 | 对话框按钮不吃语义点击（建造确认、info 屏退出） | 🔴 高 | [problems](problems/03-对话框与按钮.md) |
| 4 | 存档入口极隐蔽；`menu:load` 跳去新游戏菜单 | 🟠 中 | [problems](problems/04-存档与读档.md) |
| 5 | 地下寻路谎报 `NO_PATH`；相邻英雄走不进对方格子 | 🟠 中 | [problems](problems/05-寻路与地图.md) |
| 6 | 路线缓存 stale、两次调用间状态翻转 | 🟠 中 | [problems](problems/05-寻路与地图.md) |
| 7 | 动作实际生效却返回 `uncertain` | 🟡 低 | [problems](problems/06-协议与确认.md) |
| 8 | 随机图"城镇"候选被计时器文本污染 | 🟡 低 | [problems](problems/06-协议与确认.md) |
| 9 | `Топтание`（原地打转）提示会让 agent 误判 | 🟡 低 | [problems](problems/06-协议与确认.md) |
| 10 | `hotseat` / `lan` / `start_game` 的边界 | 🟡 说明 | [problems](problems/06-协议与确认.md) |
| 11 | 静默安装 `exit 2`：没写注册表就"找不到游戏目录" | 🟠 环境 | [problems](problems/00-安装与挂载.md) |
| 12 | attach 失败：HD Mod 版本对不上（5.2 vs 5.8） | 🔴 环境 | [problems](problems/00-安装与挂载.md) |

---

## 五、想自己复现

```powershell
# 1) 装游戏（GOG Complete）+ HotA 1.8.1 + HD Mod 5.8
# 2) 写游戏目录（非标准路径必做，否则安装器 exit 2）
reg add "HKCU\Software\HotaMcp" /v GameDir /t REG_SZ /d "D:\...\Heroes of Might and Magic 3 Complete" /f
# 3) 静默安装 MCP
HotaMcp-Setup-1.0.2.exe /S /D=D:\Heroes3\HotaMcp
# 4) 起服务 + 起游戏
Start-Process D:\Heroes3\HotaMcp\app\HotaMcp.exe -WindowStyle Hidden
Start-Process ".\h3hota HD.exe" -WorkingDirectory <游戏目录>
# 5) 用任意 MCP 客户端连 http://127.0.0.1:18773/mcp
#    Bearer token 在 %LOCALAPPDATA%\HotaMcp\connection.token
```

`tools/mcp.py` 是零依赖 MCP 客户端，`tools/play2.py` 是日常操作壳，
`tools/autoplay.py` 是第一局的挂机脚本（含全部 workaround）。

---

## 六、我怎么评价它

**做得好的**

- **协议设计**：`revision` + `operationId` + 独立"确认"证据，把"我点了吗"从"信任返回值"变成"再读一次世界"。
- **错误码是给模型看的**：17 个 `[CODE]` 不是给程序 catch 的，是给 agent 纠错的。实测确实靠它们自我恢复。
- **零 OCR**：结构签名而不是文件哈希，HD Mod / HotA 更新不会让它失效，只要求"结构在正确的位置"。
- **知识层**：1.6 MB FTS5 文档让"这条规则是什么"不必进上下文。

**局限**

- **脆弱**：一个未处理的 `OverflowException` 就让整局不可观测，且没有降级路径。
- **覆盖面**：最常用的"建设/招募/交接"链路是断的；`hotseat`、`lan` 在 `capabilities.unavailable` 里明说没做。
- **速度**：每次动作后的确认轮询决定了它更像"看一步走一步"，而不是拟人操作。

---

## 七、目录

```
README.md                    本文
problems/                    子层级一：12 个问题（现象 / 复现 / 报错原文 / 绕法）
  00-安装与挂载.md
  01-读屏崩溃.md
  02-兵格与交接.md
  03-对话框与按钮.md
  04-存档与读档.md
  05-寻路与地图.md
  06-协议与确认.md
diary/                       子层级二：战报 / 日记（逐日 + 截图 + 当时的想法）
  README.md
  第一局-空权.md
  第二局-01-第一周.md
  第二局-02-事故与读档.md
  第二局-03-运兵与收工.md
screenshots/                 每天一张地图 + 战斗/升级/酒馆/存档界面
tools/                       客户端与自动化脚本
data/                        journal-game1.jsonl · journal-game2.jsonl
                             usage-game1.jsonl · usage-game2.jsonl · turnlog-index.md
```

## 八、声明

- 仅为个人实验记录，与 `timoncool/hota-mcp` 作者无关；hota-mcp 自身的许可证见其仓库。
- 游戏素材（截图）版权归 Ubisoft / HotA 团队，仅作技术说明用途。
- 未修改游戏任何文件；`tools/` 里的脚本只通过 MCP 接口操作游戏。

## 九、归档约定

**这个仓库是「所有跟英雄无敌 3 相关的学习记录」的唯一去处**，不再另开仓库。以后每学到一条、每踩到一个坑、每打完一局，都往这里加，然后上传。

往哪写：

| 内容 | 位置 | 规则 |
| --- | --- | --- |
| 可复现的技术问题 | `problems/NN-简短标题.md` | 从 `07` 往后编号；四段式（现象 / 复现 / 原因判断 / 绕法）；同时在 `problems/README.md` 的索引表补一行 |
| 对局记录（战报 / 日记） | `diary/第N局-MM-阶段.md` | 一局拆 2–4 篇（开局、事故、收工）；逐日写清"看到什么 → 怎么想 → 做了什么 → 花了多少"，配 `screenshots/` 的图 |
| 游戏机制 / 数值 | 就近写进对应对局日记的"机制小抄"，或 `problems/06-协议与确认.md` | 附 `hota_reference` / tooltip 的原文，不凭记忆 |
| 新工具脚本 | `tools/` | 零依赖（只用标准库），顶部写一句用法 |

素材按固定流程走：

1. 每个回合结束前跑 `tools/endday.py`：截 `screenshots/dayNN-W-M.png`，并往 `data/turnlog-index.md` 追加一行（日期 / 英雄 / 位置 / 移动力 / 金币）。
2. 一局结束时，把 `%LOCALAPPDATA%\HotaMcp` 下的 `sessions\*\journal.jsonl` 与 `usage\*.jsonl` 复制成 `data/journal-gameN.jsonl` / `data/usage-gameN.jsonl`。
3. 截图统一量化到 256 色再入库（避免仓库膨胀）。

上传：

```powershell
cd D:\Heroes3\hota-mcp-report
python .publish\publish.py . ruopu01/hota-mcp-play-report "说明这一版改了什么"
```

`.publish/` 已被 `.gitignore` 忽略，只在本机存在（内含读 Windows 凭据的发布脚本，不分发）。

已知限制：本机 token 的 scope 不含 `delete_repo`，所以脚本只能更新内容、不能删仓库；废弃仓库要手动去 Settings → Danger Zone 删。
