# screenshots/

## 每日一张（`dayNN-W-M.png`）

每天结束回合前，`tools/endday.py` 会调 `debug_capture` 存一张 **1180×664 的游戏 framebuffer**
（不是桌面截图），命名规则：

```
day[日]-[周]-[月].png
day01-1-1.png   第 1 周第 1 天
day07-1-1.png   第 1 周第 7 天（第 7 天存了两次：切英雄前后各一张）
day01-2-1.png   第 2 周第 1 天（= 第 8 天）
day02-2-1.png   第 2 周第 2 天（= 第 9 天）
day03-2-1.png   第 2 周第 3 天（= 第 10 天，收工那天）
```

每一张都对应 `data/turnlog-index.md` 里的一行记录（位置 / 移动力 / 金币），**可以对账**。

## 界面特写

| 文件 | 内容 |
| --- | --- |
| `day6-adventure.png` | **第一局**第 6 天：Anabar 城下（72×72 空权，1180×664 原始尺寸） |
| `day9-after-battle.png` | **第一局**第 9 天：打完 Rogue 堆之后 |
| `tavern2.png` | 酒馆两个候选人（Rion / Jenova） |
| `town3.png` | 城镇屏：两条军阵 + 见底的资源条 |
| `marksman.png` | Archer ×13 升级成 Marksman ×13 之后 |
| `combat1.png` | 半人马战斗第一轮（2×17 Centaur） |
| `savebox.png` | 存档界面，文件名 `fish-10` |
| `day9b.png` | 地下：沙地、龙蝇巢、中立城 Ellesmere |

> `day6-adventure.png` / `day9-after-battle.png` 来自第一局（Air Supremacy），
> 未做量化，保留原始画质；其余是第二局，做了 256 色量化。

## 关于压缩

为了让仓库别太肥，所有 PNG 都用 PIL 做了 256 色量化（`MEDIANCUT`，无 dither）。
19 张图从 16.5 MB 压到 7.3 MB，肉眼看不出差别 —— 毕竟原图也只有 256 色的游戏画面。
