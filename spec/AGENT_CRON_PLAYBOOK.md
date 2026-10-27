# AGENT_CRON_PLAYBOOK.md — ml-decision-boundary

> 唯一事实源：`spec/CHARTER.md` + `spec/phases.md` + `strategy/NEXT_ROUND_THEME.md`
> 本文件只放「怎么跑」的操作规程，不重复状态（状态只在上述三处，避免多源漂移）。

## 快速入口（按顺序，每步只读一遍）

1. 读 `spec/CHARTER.md`（4.7K，仓库使命与边界）
2. 读 `spec/phases.md`（8.9K，DoD 与阶段状态）
3. 读 `strategy/NEXT_ROUND_THEME.md`（约 14K，**已精简**，历史正文在 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`）
4. 读 `strategy/NEXT_ROUND_THEME.md` 末尾的「当前全局状态」+「价值确认」两节 → 这是本轮交付的锚点

## 上下文纪律（2026-10-26 新增，因 cron 3 次 Context overflow）

- ❌ 禁止把 `NEXT_ROUND_THEME.md` 之外的历史文件整份读进上下文。
- ❌ 禁止读 `strategy/runs/` 下的历史 run log（每轮只会新增一个文件，历史不是本轮输入）。
- ✅ 需要历史交叉对照时，只读 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md` 的**指定小节**，不要整读。
- ✅ 每轮写回 `NEXT_ROUND_THEME.md` 后，若文件超过 **20K**，把旧小节迁到 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`，只保留：当前轮次状态 / 最近 6 条皇上操作记录 / 当前全局状态 / 价值确认。

## 每轮交付物（沿用既定口径，不改）

- 代码实现 + 测试（新增测试进 `tests/`，P1 必须全绿）
- `strategy/runs/{YYYY-MM-DD-HHMM}.md` 本轮 run log
- `NEXT_ROUND_THEME.md` 顶部更新「本轮状态」，末尾更新「当前全局状态」「价值确认」
- 需要皇上决策时（PR 待 Merge / ADR 待 Accepted），才在「皇上操作记录」表新增一行

## 本轮状态锚点

- 当前阶段：v12（Python API & SDK Foundation）进行中
- 当前 PR：#60（DoD #1 Python SDK），CI 6/6 SUCCESS，待皇上 Merge
- 详细状态以 `NEXT_ROUND_THEME.md` 为准
