# GEO Autopilot · 上线配置（仅剩一次性密钥，之后每日无人值守）

仓库与 workflow **均已部署上线**：
- 仓库：**https://github.com/bistuwangqiyuan/zk-geo-autopilot** （私有，引擎 + workflow 已在线）。
- workflow：**`GEO Autopilot (daily)` 已 active**（每日 cron + 手动触发）。

云端真正跑起来只差 **一次性配置 2 个 Secret**（你的凭据，本系统从不经手/打印/提交）。

## 1. 配置仓库 Secrets（Settings → Secrets and variables → Actions，或用 `gh secret set`）

| Secret | 用途 | 如何获取 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | 调用通义千问/DeepSeek 做真实 GVI 与 AI 决策 | 阿里云百炼控制台 → API-KEY |
| `GH_PAT` | clone/push 官网与知识库仓库、开告警 Issue | GitHub → Settings → Developer settings → **Fine-grained PAT**，对 `zhongke-dpu-official`、`zk-storage-kb`、`zk-geo-autopilot` 授予 **Contents: Read and write**、**Issues: Read and write** |
| `PSI_API_KEY`（可选） | PageSpeed Insights 提额 | Google Cloud Console |

```bash
gh secret set DASHSCOPE_API_KEY --repo bistuwangqiyuan/zk-geo-autopilot   # 按提示粘贴 key
gh secret set GH_PAT            --repo bistuwangqiyuan/zk-geo-autopilot   # 按提示粘贴 PAT
```

> 安全：本系统从不打印或提交任何密钥；密钥仅以仓库 Secret 注入 CI 环境变量。

## 2. 首跑验证

```bash
gh workflow run "GEO Autopilot (daily)" --repo bistuwangqiyuan/zk-geo-autopilot -f mode=ci -f gvi_limit=4
gh run watch --repo bistuwangqiyuan/zk-geo-autopilot   # 观察绿跑
```

- 绿跑后核验：
  - `official_website` 仓库出现 `chore(geo-autopilot)` 提交 → Netlify 自动部署 `goni.top`；
  - Actions artifact `geo-daily-report` 内有当日 PDF/HTML；
  - `zk-geo-autopilot` 仓库 `geo_autopilot/history/snapshot_*.json` 增加当日快照。

## 3. 让 cron 接管

无需额外操作。默认 `cron: "30 22 * * *"`（UTC）= 北京时间次日 06:30 自动运行。
如需改时间，编辑 `.github/workflows/geo-autopilot.yml` 的 `schedule`。

## 受客观约束、系统不会无人化的环节（如实告警，不伪造）

| 环节 | 原因 | 系统行为 |
| --- | --- | --- |
| GSC「请求编入索引」 | 需浏览器登录、无公开写 API、有每日配额 | 开/更新 Issue 列待办 + SOP |
| CSDN/知乎/百科/公众号 UGC 发布 | 无开放写 API、需实名 | 刷新定稿草稿 + Issue 待办 + SOP |
| 百度收录 | 需 ICP 备案 | Issue 告警，备案后再开通 |
