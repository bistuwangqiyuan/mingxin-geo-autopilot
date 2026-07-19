# 铭信 · GEO Autopilot（全自动 AI GEO 系统）

一套**云端每 4 小时无人值守、完全 AI 驱动**的铭信官网（https://mingxinstorage.xyz）
GEO（生成式引擎优化）系统。每轮自动：真实重测大模型可见性 → AI 决策与内容自进化 →
写入官网内容数据源并推送部署 → 收录推送 → 累积可检验历史 → 产出苹果视觉日报 HTML/PDF →
对受约束的人工项如实告警。

## 设计原则（贯穿全程）

- **实事求是、可复现**：所有数值由 Python 基于单一事实源（`business_plan/outputs/results.json`，
  即官网 `site/src/lib/data/company.ts` 的镜像）计算；关键实测数字全部带报告编号（R1–R9）；
  GVI 由国产大模型真实 API 采样（grade A）按公开权重合成。
- **绝不臆造 / 自我净化**：AI 内容提案先过「事实口径一致性闸门」再过写盘校验闸门，
  失败自动回滚，绝不让未校验内容上线。
- **诚实边界**：GSC 请求收录、UGC 发布、百度收录受客观约束（无公开写 API / 需实名 / 需备案），
  系统**开 Issue 告警 + 给 SOP**，绝不自动伪装完成。

## 部署链路（每 4 小时一轮）

GitHub Actions（cron 每 4h）→ clone `amd`（官网，Next.js 站点在其 `site/` 子目录）+
`mingxin-storage-kb`（知识库）→ GVI 实测（DashScope / Vercel AI Gateway）→ 决策脑
`geo_brain.py` → `apply_proposals.py` 写入 `site/src/lib/data/autopilot_faq.json`（经事实闸门）→
push `amd` → `VERCEL_DEPLOY_HOOK_URL` 触发 Vercel 项目 `mingxin-site` 重新部署
（项目未连 GitHub 自动构建；未配置 Hook 则需手动 `vercel deploy`）→
`POST {SITE_URL}/api/seo/ping`（Bearer `CRON_SECRET`，站点自持 IndexNow key 完成收录推送）→
历史快照 / 趋势 / 日报 / 告警。

## 每轮流水线（`autopilot.py`）

| 阶段 | 模块 | 说明 |
| --- | --- | --- |
| 热词挖掘 | `keyword_miner.py` | 欧美买家长尾问题（KV Cache 分层 / NVMe-oF / MI308X / 910B / TTFT / FX100），台账去重限量 |
| 真实 GVI 重测 | `seo_geo_loop/gvi_measure.py` | 多模型 × 查询集，预算/超时护栏 |
| AI 决策脑 | `geo_brain.py` | 指标→优先级 + 批评与自我批评 + 内容提案 JSON（失败回退确定性规则脑） |
| 内容自进化 | `apply_proposals.py` | 一致性闸门 + 写盘校验 + 失败回滚，落地 `site/src/lib/data/autopilot_faq.json` |
| 站外重建 | `seo_geo_loop/build_offsite_*.py` | 站外微站 / GitHub Pages 知识库 |
| 覆盖与评分 | `geo_plan/source_audit.py` · `geo_scoring.py` | 信源覆盖诚实推导 + GVI 评分 |
| 联网真测 | `indexnow_submit.py` · `live_audit.py` · `traffic_check.py` | /api/seo/ping 收录推送 + 线上核验 + GA4 信号（仅 once/ci） |
| 部署 | git commit+push + Deploy Hook | 官网 amd → Vercel（Hook 触发）· 知识库 → Pages（仅 ci） |
| 历史/趋势/日报 | `metrics.py` · `trend.py` · `build_daily_report.py` · `export_daily_pdf.py` | 快照 + 苹果风趋势图 + A4 PDF |
| 告警 | `alerting.py` | 回归/待人工项 → GitHub Issue（含数据快照 + SOP） |

## 本地运行

```bash
# 1) 最快：校验装配完整（不联网、不推送）
python geo_autopilot/autopilot.py --dry-run

# 2) 本地完整跑（真实小样 GVI、重建、报告），不 git push
python geo_autopilot/autopilot.py --once --gvi-limit 4

# 3) 单独验证 AI 决策脑 / 内容自进化
python geo_autopilot/geo_brain.py
python geo_autopilot/apply_proposals.py            # 经事实闸门
```

模式与护栏：`--dry-run | --once | --ci`，`--gvi-limit N`、`--skip-gvi`、`--no-llm`。

## 上线（GitHub Actions cron）

见 [`SETUP.md`](SETUP.md)：配置 Secrets（一次）→ `workflow_dispatch` 首跑 → cron 每 4h 接管。

## 路径自适应

`paths.py` 统一解析：本地引擎/站点为同级目录；CI 经环境变量或默认（仓库根的同级 clone）解析，
支持 `MX_GEO_PLAN`、`MX_LOOP`、`MX_OFFICIAL_WEBSITE`、`MX_KB_REPO`、`MX_WORKSPACE_ROOT`、
`MX_SITE_SUBDIR` 覆盖。站点源码根 = `official_website/site`（amd 仓库 `site/` 子目录）。
