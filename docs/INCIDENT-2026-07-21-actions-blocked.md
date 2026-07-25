# 事故复盘：站外 GEO 引擎自 2026-07-21 起停摆

复盘时间：2026-07-25
状态：**根因已确认，恢复动作待人工决策**（涉及账户付款，程序无法也不应代办）

## 一、发生了什么

`bistuwangqiyuan/zk-geo-autopilot` 的 `geo-autopilot.yml` 自 2026-07-21 起
**连续 28 次 `conclusion: failure`**。异常特征：

- job 在 **2 秒内**结束（例：run `30153997490`，10:10:06 → 10:10:08）
- **步骤总数为 0** —— runner 从未启动，因此日志是空的
- workflow 状态 `active`，仓库未归档未禁用，cron 准时触发

步骤数为 0 意味着「代码故障」「依赖安装失败」「调度未触发」全部可以排除：
问题发生在 runner 被分配之前。

## 二、根因

GitHub 返回的 check-run 注解原文：

> The job was not started because recent account payments have failed or your
> spending limit needs to be increased.

**这是账户级计费拒绝。** 两条独立证据支持"账户级"而非"本仓库级"：

1. 同一时间窗口内，账户下多个互不相关的私有仓库出现同一注解
   （`python scripts/actions_account_health.py` 可复现）
2. 完整枚举账户全部 583 个仓库（其中 421 个私有，**枚举未被截断**）后，
   本月私有仓库合计计费 **1095 分钟 / 免费额度 2000 分钟，未超额**
   （`reports/actions_usage.json`）

## 三、一个必须纠正的初始判断

最初的假设是「免费额度耗尽」。**这个假设是错的**，上面第 2 条证据已排除它。

而且用量口径本身是保守的：本次统计中所有运行的 `billable` 字段均为 0，
脚本改用 `run_duration_ms`（墙钟时长）向上取整做**上界估算**，
所以真实计费只会低于 1095 分钟，不会更高。结论方向不因口径而翻转。

顺带一个反直觉的事实：`zk-geo-autopilot` 本身**不在**用量前 15 名——
因为它每次都在 2 秒内失败，几乎没消耗分钟数。账户用量的大头是
`mingxin-marketing-cron`（326 分钟）与 `aiseoauto`（267 分钟）。

**所以：降频瘦身不能解除本次停摆。** 谁把恢复寄望于改配置，就会白等。

## 四、复现方式

```bash
# 失败模式、连续失败次数、PAT 有效期（备选根因）
python scripts/actions_diagnose.py

# GitHub 注解原文（步骤数为 0 时唯一的线索来源，日志里没有）
python scripts/actions_annotations.py

# 证明是账户级而非单仓库
python scripts/actions_account_health.py

# 账户级用量测算（用真实 run_duration_ms，非拍脑袋估算）
python scripts/actions_usage_account.py --out reports/actions_usage.json
```

## 五、恢复方案（最终由人决定）

### 必要动作（无替代路径）

在 **GitHub Settings → Billing** 处理付款方式失败或提高支出上限。
这是唯一能解除当前拒绝的动作，**涉及支出，属于人的决策**。

### 零支出的替代路径：仓库转 public

GitHub 托管 runner 对 public 仓库免费无限量。前置核验已完成：

- 全历史 4312 个对象（3928 个文本 blob）扫描：**未发现任何密钥/凭据**
- 但发现 **9 处个人邮箱地址**（同一地址，散落 9 个 blob）
  复现：`python tools/scan_sensitive.py --git-all-objects .`

也就是说：转 public 不会泄露凭据，但会把一个个人邮箱地址公开可检索。
这是 PII 暴露而非安全事故，**是否可接受由邮箱所有者本人决定**。
若决定转 public 且不希望暴露该地址，需先用 `git filter-repo` 重写历史。

### 已实施的用量瘦身（账单恢复后立刻生效）

见 `.github/workflows/geo-autopilot.yml` 头部注释。要点：

| 项 | 改动前 | 改动后 |
| --- | --- | --- |
| cron 频率 | 6 次/天 | 2 次/天 |
| `timeout-minutes` | 50 | 25 |
| pip 依赖 | 每次重装 | 缓存 |
| Playwright Chromium | 每次下载 | 缓存，命中时只装系统依赖 |
| bailian-cli（回退链第 3 顺位） | 每次全局安装 | 缓存 npm 全局目录 |

降频到 2 次/天后单次可承担更多采样，定时运行的 `--gvi-limit` 由 4 提到 8，
业务动作总量没有削减。

## 六、真正的教训：告警与被监控方同源失效

**这次停摆持续了 5 天没有被任何人发现。**

原因不是没有告警，而是告警**寄生在被监控的系统里**：引擎的告警要靠引擎运行
才能发出，runner 起不来时，它同时失去了报警能力。这是监控设计的经典错误。

治本措施已随本次改动上线：由**官网的 Vercel Cron**（另一套已长期稳定运行的
系统）每天探测本 workflow 的健康度。

- 实现：`amd/site/src/app/api/engine/autopilot-watchdog/route.ts`
- 调度：`amd/site/vercel.json`，每日 09:00 UTC
- 判定：距上次成功超过 `AUTOPILOT_STALE_HOURS`（默认 30 小时）即告警
- 行为：抓取 GitHub 注解原文 → 归类根因并给出处置建议 → 在本仓库开一个
  去重的追踪 issue → 写入 `engine_log`
- 关键设计：取不到数据时报 `unknown` 并计为 `degraded`，**绝不因为查不到就报告健康**

## 七、当前未达成的验收标准（如实声明）

原计划的 P1 验收标准是「workflow 连续 3 次 `conclusion: success`」。

**该标准目前无法达成，因为它的前置条件是账户付款问题被解决，而这不在程序的
能力范围内。** 在账单恢复之前，本仓库的任何改动都不会让 runner 启动。

已达成的部分：根因确认（可复现）、用量瘦身（恢复后生效）、跨系统看门狗
（已上线，下次停摆当天即可发现）。
