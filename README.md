# zk-geo-autopilot

铭信官网（https://mingxinstorage.xyz）**全自动 AI GEO+SEO 系统**（云端每 4 小时无人值守；引擎仓库名沿用不变）。

- 引擎与编排见 [`geo_autopilot/`](geo_autopilot/)（入口 `autopilot.py`）。
- 部署链路：GitHub Actions cron（每 4h）→ clone `amd`（官网，Next.js 站点在其 `site/` 子目录）+ `mingxin-storage-kb`（知识库）→ 真实 GVI 重测（多模型直连）→ AI 决策脑 → 内容自进化（经事实闸门，写入 `site/src/lib/data/autopilot_faq.json`）→ push `amd` → `VERCEL_DEPLOY_HOOK_URL` 触发 Vercel 项目 `mingxin-site` 部署（未配置则需手动 `vercel deploy`）→ `/api/seo/ping` IndexNow 收录推送（Bearer `CRON_SECRET`）→ 历史快照 → 苹果视觉日报 HTML/PDF → 告警。
- 多模型层（`geo_plan/llm_providers.py`）：通义/DeepSeek/智谱 GLM/Kimi/腾讯混元/讯飞星火/豆包/Claude/Gemini 直连各家官方 API——密钥在即自动纳入 GVI 实测与决策脑回退链，缺失/欠费/失效时优雅跳过并如实标注，绝不编造。
- 一次性密钥配置见 [`SETUP.md`](SETUP.md)：`AI_GATEWAY_API_KEY`、`DASHSCOPE_API_KEY`、`GH_PAT`、`CRON_SECRET` 必需；九家模型 `*_API_KEY` 与 `VERCEL_DEPLOY_HOOK_URL`、`MX_GA4_ID`/`GA4_PROPERTY_ID`/`GA4_SA_JSON` 可选。
- 单一事实源：`business_plan/outputs/results.json`（= 官网 `site/src/lib/data/company.ts` 的镜像）；关键实测数字全部带报告编号（R1–R9）。

纪律：所有数值可复现、单一事实源；预测标注「规划假设、非承诺」；受客观约束的人工项（GSC/UGC/ICP/未配 Deploy Hook 的部署）如实开 Issue 告警或记录跳过，绝不伪造完成。
