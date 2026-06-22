# zk-geo-autopilot

中科存储官网 **全自动 AI GEO 系统**（云端每日无人值守）。

- 引擎与编排见 [`geo_autopilot/`](geo_autopilot/)（入口 `autopilot.py`）。
- 每日由 GitHub Actions cron 运行：真实 GVI 重测 → AI 决策与内容自进化（经 verify 闸门）→ 重建并部署官网/知识库 → IndexNow → 历史快照 → 苹果视觉日报 HTML/PDF → 告警。
- 一次性密钥配置见 [`SETUP.md`](SETUP.md)。

纪律：所有数值可复现、单一事实源；预测标注「规划假设、非承诺」；受客观约束的人工项（GSC/UGC/ICP）如实开 Issue 告警，绝不伪造完成。
