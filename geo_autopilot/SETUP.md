# 铭信 GEO Autopilot · 上线配置（仅剩一次性密钥，之后每 4 小时无人值守）

引擎仓库与 workflow：
- 仓库：**https://github.com/bistuwangqiyuan/zk-geo-autopilot** （私有，引擎 + workflow；仓库名沿用不变）。
- workflow：**`GEO Autopilot (every 4h)`**（每 4 小时 cron + 手动触发）。

部署链路（一图流）：GitHub Actions 每 4h → clone `amd` + `mingxin-storage-kb` →
GVI 实测（DashScope / AI Gateway）→ 决策脑 → `apply_proposals` 写
`site/src/lib/data/autopilot_faq.json` → push `amd` → `VERCEL_DEPLOY_HOOK_URL` 触发
Vercel 项目 `mingxin-site` 部署（未配置则需手动 `vercel deploy`）→
`/api/seo/ping` IndexNow 收录推送（Bearer `CRON_SECRET`）→ 日报/告警。

## 1. 配置仓库 Secrets（Settings → Secrets and variables → Actions，或用 `gh secret set`）

| Secret | 必需 | 用途 | 如何获取 |
| --- | --- | --- | --- |
| `AI_GATEWAY_API_KEY` | 是 | Vercel AI Gateway（首选 LLM 路：决策脑 + 热词挖掘） | Vercel Dashboard → AI Gateway → API Key |
| `DASHSCOPE_API_KEY` | 是 | 通义千问/DeepSeek 真实 GVI 采样 + LLM 回退路 | 阿里云百炼控制台 → API-KEY |
| `GH_PAT` | 是 | clone/push 官网与知识库仓库、开告警 Issue | GitHub → Settings → Developer settings → **Fine-grained PAT**，对 `amd`、`mingxin-storage-kb`、`zk-geo-autopilot` 授予 **Contents: Read and write**、**Issues: Read and write** |
| `CRON_SECRET` | 是 | 调用铭信站点自带接口 `/api/seo/ping`、`/api/engine/*`（Bearer 鉴权） | 与 Vercel 项目 `mingxin-site` 环境变量中的 `CRON_SECRET` 保持一致 |
| `VERCEL_DEPLOY_HOOK_URL` | 可选 | push `amd` 后触发 Vercel 重新部署（项目未连 GitHub 自动构建；未配置则需手动 `vercel deploy`） | Vercel 项目 `mingxin-site` → Settings → Git → Deploy Hooks |
| `MX_GA4_ID` | 可选 | GA4 埋码 Measurement ID（流量信号·四步法第 4 步） | GA4 管理后台 |
| `GA4_PROPERTY_ID` + `GA4_SA_JSON` | 可选 | GA4 Data API 读取流量信号（服务账号 JSON） | Google Cloud Console + GA4 属性授权 |

```bash
gh secret set AI_GATEWAY_API_KEY     --repo bistuwangqiyuan/zk-geo-autopilot
gh secret set DASHSCOPE_API_KEY      --repo bistuwangqiyuan/zk-geo-autopilot
gh secret set GH_PAT                 --repo bistuwangqiyuan/zk-geo-autopilot
gh secret set CRON_SECRET            --repo bistuwangqiyuan/zk-geo-autopilot
gh secret set VERCEL_DEPLOY_HOOK_URL --repo bistuwangqiyuan/zk-geo-autopilot   # 可选
```

> 安全：本系统从不打印或提交任何密钥；密钥仅以仓库 Secret 注入 CI 环境变量。

## 2. 首跑验证

```bash
gh workflow run "GEO Autopilot (every 4h)" --repo bistuwangqiyuan/zk-geo-autopilot -f mode=ci -f gvi_limit=4
gh run watch --repo bistuwangqiyuan/zk-geo-autopilot   # 观察绿跑
```

- 绿跑后核验：
  - `amd` 仓库出现 `chore(geo-autopilot)` 提交，且 `site/src/lib/data/autopilot_faq.json` 有新增条目；
  - 配置了 `VERCEL_DEPLOY_HOOK_URL` 时，Vercel 项目 `mingxin-site` 出现新部署，
    https://mingxinstorage.xyz 内容刷新（未配置则手动 `vercel deploy`）；
  - Actions artifact `geo-daily-report` 内有当日 PDF/HTML；
  - `zk-geo-autopilot` 仓库 `geo_autopilot/history/snapshot_*.json` 增加当日快照。

## 3. 让 cron 接管

无需额外操作。默认每 4 小时一次（UTC 00:30/04:30/08:30/12:30/16:30/20:30）
= 北京时间 08:30/12:30/16:30/20:30/00:30/04:30。
如需改时间，编辑 `.github/workflows/geo-autopilot.yml` 的 `schedule`。

## 受客观约束、系统不会无人化的环节（如实告警，不伪造）

| 环节 | 原因 | 系统行为 |
| --- | --- | --- |
| GSC「请求编入索引」 | 需浏览器登录、无公开写 API、有每日配额 | 开/更新 Issue 列待办 + SOP |
| CSDN/知乎/百科/公众号 UGC 发布 | 无开放写 API、需实名 | 刷新定稿草稿 + Issue 待办 + SOP |
| 百度收录 | 需 ICP 备案 | Issue 告警，备案后再开通 |
| Vercel 部署（未配 Deploy Hook 时） | 项目未连 GitHub 自动构建 | 如实记录跳过，需人工 `vercel deploy` |
