# mingxin-geo-autopilot

铭信官网（https://mingxinstorage.xyz）**全自动 AI GEO+SEO 系统**（云端每天 2 次无人值守运行）。

- 引擎与编排见 [`geo_autopilot/`](geo_autopilot/)（入口 `autopilot.py`）。
- 部署链路：GitHub Actions cron（每天 2 次）→ clone `mingxin-storage-kb`（知识库，公开仓）→ 真实 GVI 重测（多模型直连）→ AI 决策脑 → 内容自进化（经事实闸门，写 `geo_autopilot/outputs/autopilot_faq.json` 并 POST 到官网 `/api/engine/autopilot-faq` 落库上线）→ `/api/seo/ping` IndexNow 收录推送（Bearer `CRON_SECRET`）→ 历史快照 → 苹果视觉日报 HTML/PDF → 告警。

  > 2026-08-08 变更：不再 clone/push 私有的官网仓 `amd`。原链路要求本公开仓的 CI 持有私有主仓的**写**权限，且实测三处同时断着——缺 `GH_PAT` 连 clone 都做不到（本 workflow 因此连续 20 次失败、静默 5 天）、`VERCEL_DEPLOY_HOOK_URL` 未配置（推上去也不会部署）、**站点代码从来没有读过 `autopilot_faq.json`**（即整条链路即便跑通也不产生任何对外效果）。改走站点 API 后，跨仓写权限的需求整个消失，产出直接出现在 `/faq` 与 `/en/faq`。
- 多模型层（`geo_plan/llm_providers.py`）：通义/DeepSeek/智谱 GLM/Kimi/腾讯混元/讯飞星火/豆包/Claude/Gemini 直连各家官方 API——密钥在即自动纳入 GVI 实测与决策脑回退链，缺失/欠费/失效时优雅跳过并如实标注，绝不编造。
- 一次性密钥配置见 [`SETUP.md`](SETUP.md)：`AI_GATEWAY_API_KEY`、`DASHSCOPE_API_KEY`、`CRON_SECRET` 必需；九家模型 `*_API_KEY` 与 `GH_PAT`（仅用于回写公开的知识库仓）、`MX_GA4_ID`/`GA4_PROPERTY_ID`/`GA4_SA_JSON` 可选。
- 单一事实源：`business_plan/outputs/results.json`（= 官网 `site/src/lib/data/company.ts` 的镜像）；关键实测数字全部带报告编号（R1–R9）。

## 本仓库是公开的，这一点约束了什么

2026-07-26 从私有仓库 `zk-geo-autopilot`（已归档）迁来，原因是账户级 Actions 计费拒绝
导致引擎停摆 5 天，而 GitHub 托管 runner 对公开仓库免费无限量。完整复盘见
[`docs/INCIDENT-2026-07-21-actions-blocked.md`](docs/INCIDENT-2026-07-21-actions-blocked.md)。

由此产生两条必须遵守的纪律：

1. **引擎每次运行都会把数据回写提交，提交即对外发布。** 因此 workflow 在 `git add`
   之后、`git commit` 之前强制过一道敏感信息闸门（`tools/scan_sensitive.py --staged .`），
   命中即失败且不提交。这一行不得加 `|| true`。
2. **凭据与结构性敏感产物一律不入库**，规则见 [`.gitignore`](.gitignore)，与扫描器的
   `PATH_RULES` 对齐，两处口径必须一致。

纪律：所有数值可复现、单一事实源；预测标注「规划假设、非承诺」；受客观约束的人工项（GSC/UGC/ICP/未配 Deploy Hook 的部署）如实开 Issue 告警或记录跳过，绝不伪造完成。
