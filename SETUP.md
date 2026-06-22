# GEO Autopilot · 上线配置（一次性人工，唯一需人工的环节）

云端全自动运行只需 **一次性配置密钥**，之后每日 cron 无人值守。

## 1. 创建自治仓库

```bash
# 在工作区根目录运行：装配最小引擎到 ../zk-geo-autopilot 并 git init + commit
python geo_autopilot/make_repo.py

cd ../zk-geo-autopilot
gh repo create zk-geo-autopilot --private --source . --push
```

## 2. 配置仓库 Secrets（Settings → Secrets and variables → Actions）

| Secret | 用途 | 如何获取 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | 调用通义千问/DeepSeek 做真实 GVI 与 AI 决策 | 阿里云百炼控制台 → API-KEY |
| `GH_PAT` | clone/push 官网与知识库仓库、开告警 Issue | GitHub → Settings → Developer settings → **Fine-grained PAT**，对 `zhongke-dpu-official`、`zk-storage-kb`、`zk-geo-autopilot` 授予 **Contents: Read and write**、**Issues: Read and write** |
| `PSI_API_KEY`（可选） | PageSpeed Insights 提额 | Google Cloud Console |

> 安全：本系统从不打印或提交任何密钥；密钥仅以仓库 Secret 注入 CI 环境变量。

## 3. 首跑验证

```bash
gh workflow run "GEO Autopilot (daily)" -f mode=ci -f gvi_limit=4   # 小样快验
gh run watch                                                        # 观察绿跑
```

- 绿跑后核验：
  - `official_website` 仓库出现 `chore(geo-autopilot)` 提交 → Netlify 自动部署 `goni.top`；
  - Actions artifact `geo-daily-report` 内有当日 PDF/HTML；
  - `zk-geo-autopilot` 仓库 `geo_autopilot/history/snapshot_*.json` 增加当日快照。

## 4. 让 cron 接管

无需额外操作。默认 `cron: "30 22 * * *"`（UTC）= 北京时间次日 06:30 自动运行。
如需改时间，编辑 `.github/workflows/geo-autopilot.yml` 的 `schedule`。

## 受客观约束、系统不会无人化的环节（如实告警，不伪造）

| 环节 | 原因 | 系统行为 |
| --- | --- | --- |
| GSC「请求编入索引」 | 需浏览器登录、无公开写 API、有每日配额 | 开/更新 Issue 列待办 + SOP |
| CSDN/知乎/百科/公众号 UGC 发布 | 无开放写 API、需实名 | 刷新定稿草稿 + Issue 待办 + SOP |
| 百度收录 | 需 ICP 备案 | Issue 告警，备案后再开通 |
