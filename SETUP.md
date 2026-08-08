# 铭信 GEO Autopilot · 上线配置（仅剩一次性密钥，之后每天 2 次无人值守）

引擎仓库与 workflow：
- 仓库：**https://github.com/bistuwangqiyuan/mingxin-geo-autopilot** （**公开**，引擎 + workflow；公开是为绕开账户级 Actions 计费拒绝，见 docs/INCIDENT-2026-07-21-actions-blocked.md）。
- workflow：**`GEO Autopilot (twice daily)`**（每天 2 次 cron + 手动触发）。

部署链路（一图流）：GitHub Actions 每天 2 次 → clone `mingxin-storage-kb`（公开仓）→
GVI 实测（DashScope / AI Gateway）→ 决策脑 → `apply_proposals` 写
`geo_autopilot/outputs/autopilot_faq.json` 并 POST 到官网
`/api/engine/autopilot-faq` 落库（Bearer `CRON_SECRET`，即时生效于 `/faq`、`/en/faq`）→
`/api/seo/ping` IndexNow 收录推送 → 日报/告警。

> 2026-08-08 起**不再需要 `GH_PAT` 才能跑**。原链路要 clone 并 push 私有的官网仓 `amd`，
> 缺 PAT 时流水线直接 exit 1——这正是本 workflow 连续 20 次失败、静默 5 天的原因。
> 排查发现引擎对 `amd` 的全部依赖只是「写一个自己产出的 JSON 再读回来」，而站点代码
> **从未读过那个文件**。改走站点 API 后，公开仓 CI 不必再持有私有主仓写权限。

## 1. 配置仓库 Secrets（Settings → Secrets and variables → Actions，或用 `gh secret set`）

| Secret | 必需 | 用途 | 如何获取 |
| --- | --- | --- | --- |
| `AI_GATEWAY_API_KEY` | 是 | Vercel AI Gateway（首选 LLM 路：决策脑 + 热词挖掘） | Vercel Dashboard → AI Gateway → API Key |
| `DASHSCOPE_API_KEY` | 是 | 通义千问/DeepSeek 真实 GVI 采样 + LLM 回退路 | 阿里云百炼控制台 → API-KEY |
| `CRON_SECRET` | 是 | 调用铭信站点接口 `/api/seo/ping`、`/api/engine/*`（含内容自进化落库口，Bearer 鉴权） | 与 Vercel 项目 `mingxin-site` 环境变量中的 `CRON_SECRET` 保持一致 |
| `GH_PAT` | 可选 | 仅用于回写**公开的**知识库仓 `mingxin-storage-kb`、开告警 Issue。缺失时知识库回写会如实记为推送失败，主链路不受影响 | Fine-grained PAT，只需对 `mingxin-storage-kb`、`mingxin-geo-autopilot` 授予 Contents/Issues 读写；**不要**再授予私有仓 `amd` 的权限 |
| `MX_GA4_ID` | 可选 | GA4 埋码 Measurement ID（流量信号·四步法第 4 步） | GA4 管理后台 |
| `GA4_PROPERTY_ID` + `GA4_SA_JSON` | 可选 | GA4 Data API 读取流量信号（服务账号 JSON） | Google Cloud Console + GA4 属性授权 |
| `TONGYI_API_KEY` | 可选* | 通义千问直连（DashScope OpenAI 兼容；与 `DASHSCOPE_API_KEY` 二存一即可） | 阿里云百炼控制台 |
| `DEEPSEEK_API_KEY` | 可选* | DeepSeek 官方 API：GVI 实测引擎 + 决策脑回退链 | platform.deepseek.com |
| `GLM_API_KEY` | 可选* | 智谱 GLM：GVI 实测引擎 + 决策脑回退链 | open.bigmodel.cn |
| `MOONSHOT_API_KEY` | 可选* | Kimi：GVI 实测引擎 + 决策脑回退链 | platform.moonshot.cn |
| `HUNYUAN_API_KEY` | 可选* | 腾讯混元（OpenAI 兼容端点） | 腾讯云控制台 |
| `SPARK_API_KEY` | 可选* | 讯飞星火（格式 `APIKey:APISecret`） | 讯飞开放平台 |
| `DOUBAO_API_KEY` | 可选* | 豆包（火山方舟） | 火山引擎控制台 |
| `ANTHROPIC_API_KEY` | 可选* | Claude：海外引擎可见度实测 | console.anthropic.com |
| `GEMINI_API_KEY` | 可选* | Gemini（OpenAI 兼容端点）：海外引擎可见度实测 | Google AI Studio |

> \* 多模型引擎密钥全部可选：密钥在即自动纳入 GVI 实测与决策脑回退链
> （`geo_plan/llm_providers.py` 统一调用层），缺失/欠费/失效时优雅跳过并如实标注，绝不编造数据。

```bash
gh secret set AI_GATEWAY_API_KEY     --repo bistuwangqiyuan/mingxin-geo-autopilot
gh secret set DASHSCOPE_API_KEY      --repo bistuwangqiyuan/mingxin-geo-autopilot
gh secret set CRON_SECRET            --repo bistuwangqiyuan/mingxin-geo-autopilot
gh secret set GH_PAT                 --repo bistuwangqiyuan/mingxin-geo-autopilot   # 可选，仅知识库回写
```

> 安全：本系统从不打印或提交任何密钥；密钥仅以仓库 Secret 注入 CI 环境变量。

## 2. 首跑验证

```bash
python scripts/verify_secrets.py       # 先问「能不能跑成」，别触发一次撞一次墙
python scripts/trigger_and_watch.py    # 触发 + 盯到结束 + 按验收标准判定
```

`trigger_and_watch.py` 之所以不只看 Actions 的绿灯：workflow 里绝大多数业务步骤
都带 `|| true`（单点失败不该拖垮整条流水线），所以 `conclusion=success` **不等于**
每一步都成功。它会把 `run_log.json` 一并读回来核对各阶段，并比对时间戳——运行若
在回写提交前就失败，仓库里留着的是上一轮的记录，此时它判不通过而非拿旧数据充数。

退出码：0 验收通过 / 1 不通过 / 2 无法判定。可直接被定时任务或告警脚本消费。

冒烟用 `--gvi-limit 4`；重建基线用默认的 `0`（全量采样）。

- 绿跑后核验：
  - `amd` 仓库出现 `chore(geo-autopilot)` 提交，且 `site/src/lib/data/autopilot_faq.json` 有新增条目；
  - 配置了 `VERCEL_DEPLOY_HOOK_URL` 时，Vercel 项目 `mingxin-site` 出现新部署，
    https://mingxinstorage.xyz 内容刷新（未配置则手动 `vercel deploy`）；
  - Actions artifact `geo-daily-report` 内有当日 PDF/HTML；
  - `mingxin-geo-autopilot` 仓库 `geo_autopilot/history/snapshot_*.json` 增加当日快照。

## 3. 让 cron 接管

无需额外操作。默认每天 2 次（UTC 00:30 / 12:30）= 北京时间 08:30 / 20:30。
降频依据见 docs/INCIDENT-2026-07-21-actions-blocked.md：6 次/天对日更站点本就过量，
降频后单次采样上限由 4 提到 8，业务动作总量未削减。
如需改时间，编辑 `.github/workflows/geo-autopilot.yml` 的 `schedule`。

## 受客观约束、系统不会无人化的环节（如实告警，不伪造）

| 环节 | 原因 | 系统行为 |
| --- | --- | --- |
| GSC「请求编入索引」 | 需浏览器登录、无公开写 API、有每日配额 | 开/更新 Issue 列待办 + SOP |
| CSDN/知乎/百科/公众号 UGC 发布 | 无开放写 API、需实名 | 刷新定稿草稿 + Issue 待办 + SOP |
| 百度收录 | 需 ICP 备案 | Issue 告警，备案后再开通 |
| Vercel 部署（未配 Deploy Hook 时） | 项目未连 GitHub 自动构建 | 如实记录跳过，需人工 `vercel deploy` |
