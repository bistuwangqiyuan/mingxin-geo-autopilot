# 铭信官网 · GEO+SEO 提升闭环（seo_geo_loop）

一个**透明、可复现、Python 计算**的 GEO+SEO 度量与站外发布工具集。它用一个确定性的
「GEO+SEO 就绪度综合指数（CRI, 0–100）」对**线上** mingxinstorage.xyz 做 HTTP 抓取审计，
产出站外知识微站与 GitHub Pages 知识库（mingxin-storage-kb），并用 `bl` 对真实大模型
重测 GEO 可见性指数（GVI）作诚实对照，最后生成苹果视觉的 HTML→PDF 正式报告。

## 与官网（amd 仓库）的新对接方式

- 官网为 **Next.js 站点**：GitHub `bistuwangqiyuan/amd` 仓库 `site/` 子目录，Vercel 部署到
  **https://mingxinstorage.xyz**（本仓库 `../official_website` 即该仓库的 clone，供 git 取 commit）。
- 站内结构化数据/答案块/robots/llms.txt/sitemap 由**站点自身内容引擎**负责——旧的
  `build_site.py` 静态构建闭环已退役，`run_loop.py` 如实跳过重建（exit 0），历史闭环产物
  保留在 `outputs/loop_results*.json` 与 `outputs/snapshots/`。
- 收录提交走站点自带 API：`POST /api/seo/ping`（IndexNow + 百度主动推送 + WebSub，
  `Authorization: Bearer CRON_SECRET`）；内容引擎接口为 `/api/engine/*`（同鉴权）。
- 事实单一来源：`business_plan/outputs/results.json` ↔ 官网 `site/src/lib/data/company.ts`
  同源镜像，脚本经 `site_facts.py` 统一取用；**所有实测数字附签字级报告编号 R1–R9**
  （证据页 https://mingxinstorage.xyz/evidence），R9 为华为 Atlas 910B 昇腾平台口径、须标注。
- env 变量前缀统一 `MX_`：`MX_SITE_URL` / `MX_SITE_HOST` / `MX_INDEXNOW_KEY` / `CRON_SECRET`。

## 实事求是的两条分数线（务必区分）

| 分数 | 含义 | 性质 |
|---|---|---|
| **CRI** | GEO+SEO「就绪度」综合指数（0–100） | 对线上页面的**确定性 HTTP 抓取审计**（`readiness_audit.py`）；给定同一份线上 HTML 可逐行复算；网络失败时如实记录 error，不编造分数 |
| **GVI** | 真实大模型在用户提问时是否提及/引用铭信 | 由站外信源随时间积累决定；**站内改动不会在一次会话内拉升 GVI**，本仓库只如实重测、诚实对照，并给出**标注为规划区间**的预测 |

> 诚实纪律：不臆造外部 sameAs 档案、不伪造测评、不隐藏文字、不堆砌关键词；
> 所有站内事实单一来源于 `results.json`（↔ `company.ts`）；预测一律标注「规划、非承诺」。

## CRI 五支柱（权重公开、可调，和=1）

| 支柱 | 权重 | 口径（节选） |
|---|---|---|
| A 技术 SEO | 25% | title/desc/H1/canonical/hreflang/OG+Twitter/JSON-LD/lang/viewport/图片 alt/内链 + 站级 sitemap/robots/seo-ping/manifest |
| B AI 抓取与可达 | 20% | robots 放行 AI bot、声明 sitemap；llms.txt / llms-full.txt 覆盖；sitemap 覆盖全站 |
| C 结构化数据完备度 | 20% | Organization(富化)/WebSite(SearchAction)/Product(FX100 含命名沿革 alternateName)/FAQPage/BreadcrumbList/TechArticle/Person/DefinedTermSet |
| D 答案优先/可抽取性 | 20% | 问句式 H2 + 速答关键事实块 + 规格表 + FAQ + 术语 + 来源标注（R1–R9）密度 |
| E 实体一致性 & E-E-A-T | 15% | 实体名（铭信（天津）半导体设备有限公司/Mingxin）与联系方式一致、新指标口径在页（吞吐 +29–40%、TTFT ↓26–32% 等）且旧口径数字清零、可见更新时间、作者归属 |

`CRI = 100 · Σ wᵢ·支柱ᵢ`。审计页面：`/`、`/products`、`/evidence`、`/faq`、`/solutions`、`/about`、`/en`。

## 站内 GEO 杠杆清单（levers.py）

`g1`–`g13` 保留为**铭信口径的站内 GEO 检查清单**与历史闭环产物的解读依据
（Organization 实体富化、FX100 Product schema 含 AISSD5000/WS5000/GP5000 命名沿革、
BreadcrumbList、SearchAction、答案优先块、llms-full、真实 sameAs、规格口径一致性、
Speakable、性能就绪等）。落地由站点内容引擎负责，开关读写函数保留 API 兼容但为 no-op。

## 真实测评 + 站外发布脚本

- `readiness_audit.py`：线上 CRI 审计（HTTP 抓取 mingxinstorage.xyz，`--v2` 启用 8 个新子项）→ `outputs/snapshots/`。
- `live_audit.py`：线上收录/排名（agent web_search 实查）+ 在线技术 SEO 确定性核对 → `outputs/live_status.json`、追加 `seo/data/serp_observations.csv`。
- `lighthouse_psi.py`：线上性能真测，PSI(PageSpeed Insights) 优先、限流时退回 Playwright/CDP 实验室测量 → `outputs/lighthouse.json`。
- `indexnow_submit.py`：首选站点 `/api/seo/ping`（Bearer `CRON_SECRET`）；备选 `MX_INDEXNOW_KEY` 直连 IndexNow；如实记录各端点真实响应 → `outputs/indexnow_submit.json`。
- `build_offsite_site.py`：单一数据源生成苹果风站外知识微站 → `offsite_site/`（EdgeOne 部署目录；主题：FX 系列 / KV Cache 分层 / 国产算力适配 / 证据库 R1–R9 / 消歧 FAQ）。
- `build_offsite_github.py`：组装 GitHub Pages 知识库 → `offsite_github/`（发布仓库 `mingxin-storage-kb`，线上 `https://bistuwangqiyuan.github.io/mingxin-storage-kb/`）。
- `make_geo_kit_en.py`：把已过闸门的英文问答改写为 Medium/Quora/LinkedIn 成品包 → `geo_plan/offsite/en_kit/`。
- `gvi_measure.py`：真实大模型 GVI 重测与对照（词表取 `geo_plan/geo_config.py` 的铭信别名/竞品表）。
- `probe_liveness.py` / `_update_live_status.py`：批量存活探测 / 部署后线上复核（Vercel + /api/seo/ping 口径）。

## 目录与产物

```
seo_geo_loop/
  site_facts.py         # 事实 shim（results.json ↔ company.ts 同源镜像）
  readiness_audit.py    # 线上 CRI v1/v2 确定性审计（HTTP 抓取）
  levers.py             # 站内 GEO 杠杆清单（g1–g13，铭信口径；no-op 兼容层）
  run_loop.py           # 静态重建闭环退役说明（诚实跳过，exit 0）
  live_audit.py         # 线上收录/排名/技术 SEO 真测
  lighthouse_psi.py     # 线上性能真测（PSI→Playwright 实验室兜底）
  indexnow_submit.py    # /api/seo/ping + IndexNow 提交（真实响应落盘）
  build_offsite_site.py # 站外知识微站（EdgeOne 部署目录）
  build_offsite_github.py # GitHub Pages 知识库（mingxin-storage-kb）
  make_geo_kit_en.py    # 英文站外成品包（Medium/Quora/LinkedIn）
  gvi_measure.py        # 真实大模型 GVI 重测与对照
  charts.py             # 苹果风格复现图（matplotlib）
  build_report_html.py  # 苹果视觉 HTML 报告
  export_report_pdf.py  # Playwright A4 PDF
  run.py                # 一键复现编排器
  outputs/
    snapshots/*.json    # CRI 快照（历史逐轮 + 线上审计）
    loop_results.json / loop_results_v2.json   # 历史闭环产物（保留可追溯）
    live_status.json / lighthouse.json / indexnow_submit.json / offsite_published.json
    gvi_compare.json / gvi_end/raw/**
    figures/*.png
    铭信-SEO-GEO提升与站外发布报告.html
../铭信-SEO-GEO提升与站外发布报告.pdf   # 根目录正式 PDF
```

## 复现

```bash
cd seo_geo_loop
python run.py                 # 全流程（线上审计 + 真测 + 站外目录 + 报告）
python run.py --skip-net      # 跳过联网线上真测
python run.py --skip-gvi      # 跳过联网 GVI
python readiness_audit.py --label check --v2   # 单次线上 v2 审计
```

确定性部分无随机、无手绘；GVI 部分为真实 API 采样（原始回答落盘可查）；
联网步骤失败时如实记录 error，不编造结果。

## GSC CLI（免浏览器的 Search Console 自动化）

`gsc_cli.py` 用纯标准库（无需 pip）+ Google OAuth 一次性授权，缓存刷新令牌后即可无人值守调用 Search Console API。

```bash
python gsc_cli.py setup-help          # 一次性配置指南（Google Cloud 建 OAuth 桌面客户端）
python gsc_cli.py auth                # 一次性授权（之后免登录）
python gsc_cli.py sites               # 列出已验证属性
python gsc_cli.py sitemaps            # 列出已提交 sitemap
python gsc_cli.py submit-sitemap      # 提交/重提 https://mingxinstorage.xyz/sitemap.xml
python gsc_cli.py inspect https://mingxinstorage.xyz/products   # 单页收录状态（只读）
python gsc_cli.py inspect-batch       # 批量收录状态（默认读线上 sitemap）-> outputs/gsc_inspect_batch.json
python gsc_cli.py analytics --days 28 --dimensions query     # 搜索表现
```

- 凭据与令牌存于 `secrets/`（已 gitignore，绝不入库）；本工具不保存谷歌密码。
- **「请求编入索引」无公开 API**（谷歌仅对 JobPosting/BroadcastEvent 开放 Indexing API），
  该动作只能走浏览器；本仓库其余收录/sitemap/数据查询均可由本 CLI 无浏览器完成。
