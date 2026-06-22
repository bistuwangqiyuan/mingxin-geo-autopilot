# 中科存储官网 · GEO+SEO 提升闭环（seo_geo_loop）

一个**透明、可复现、Python 计算**的站内 GEO+SEO 优化闭环。它用一个确定性的
「站内 GEO+SEO 就绪度综合指数（CRI, 0–100）」驱动 **audit → 改站 → 重建 → 自检 → 重审**
的循环（最多 10 轮），把 CRI 推到诚实最高值；同时用 `bl` 对真实大模型重测一次
GEO 可见性指数（GVI）作诚实对照，并产出苹果视觉的 HTML→PDF 正式报告。

## 实事求是的两条分数线（务必区分）

| 分数 | 含义 | 性质 |
|---|---|---|
| **CRI** | 站内 GEO+SEO「就绪度」综合指数（0–100） | 我们**真正可控**；脚本确定性扫描官网 HTML 计算，无随机、无网络、可逐行复算 |
| **GVI** | 真实大模型在用户提问时是否提及/引用中科存储 | 由站外信源随时间积累决定；**站内改动不会在一次会话内拉升 GVI**，本仓库只如实重测、诚实对照，并给出**标注为规划区间**的预测 |

> 诚实纪律：不臆造外部 sameAs 档案、不伪造测评、不隐藏文字、不堆砌关键词；
> 所有站内事实单一来源于 `business_plan/outputs/results.json`；预测一律标注「规划、非承诺」。

## CRI 五支柱（权重公开、可调，和=1）

| 支柱 | 权重 | 口径（节选） |
|---|---|---|
| A 技术 SEO | 25% | title/desc/H1/canonical/hreflang/OG+Twitter/JSON-LD/lang/viewport/图片 alt/内链 + 站级 sitemap/robots/indexnow/manifest |
| B AI 抓取与可达 | 20% | robots 放行 AI bot、声明 sitemap；llms.txt / llms-full.txt 覆盖；sitemap 覆盖全站 |
| C 结构化数据完备度 | 20% | Organization(富化)/WebSite(SearchAction)/Product/FAQPage/BreadcrumbList/TechArticle/Person/DefinedTermSet |
| D 答案优先/可抽取性 | 20% | 问句式 H2 + 速答关键事实块 + 规格表 + FAQ + 术语 + 来源标注密度 |
| E 实体一致性 & E-E-A-T | 15% | 实体名/规格口径一致、联系方式 NAP、可见更新时间、作者归属、实体富化锚点 |

`CRI = 100 · Σ wᵢ·支柱ᵢ`，给定站点输入完全确定。

## 白帽杠杆组（由 `_geo_levers.json` 开关，run_loop 逐轮累计启用）

第一阶段（CRI v1，第 1–10 轮）：
`g1` Organization 实体富化 · `g2` WS7000 Product schema · `g3` 全站 BreadcrumbList ·
`g4` WebSite SearchAction · `g5` 核心人物 Person schema · `g6` 抓取/社媒头部富化 ·
`g7` 答案优先「速答·关键事实」块 · `g8` llms-full 全站覆盖 + 可见更新时间。

第二阶段（CRI v2，第 11–15 轮，全新真实杠杆，绝不重复刷分）：
`g9` 真实站外实体锚点 sameAs（仅写已上线实测 200 的 URL）· `g10` 答案优先块全覆盖 ·
`g11` 全站规格单位排版一致 · `g12` 媒体 decoding/lazy + 首页 WebPage+Speakable + 面包屑 ·
`g13` 性能就绪（关键 CSS 预加载 + 字体显示 + 预连接）。

> CRI v2 在 v1 五支柱上新增 8 个确定性子项 → 更严格的新刻度；v1 终值 99.01、v2 终值 98.1，
> 均突破第一阶段 97.9 上限（v1/v2 为不同刻度，如实并列）。
> 缺省（无 `_geo_levers.json`，如直接 `python build_site.py`）= 全部开启 = 最佳站点。

## 真实测评 + 站外发布脚本

- `live_audit.py`：线上 goni.top 收录/排名（agent web_search 实查）+ 在线技术 SEO 确定性核对 → `outputs/live_status.json`、追加 `seo/data/serp_observations.csv`。
- `lighthouse_psi.py`：线上性能真测，PSI(PageSpeed Insights) 优先、429 时退回 Playwright/CDP 实验室测量 → `outputs/lighthouse.json`。
- `build_offsite_site.py`：单一数据源生成苹果风站外知识微站 → `offsite_site/`（EdgeOne 部署目录，已上线 `manju-studio-dpdu9752l6os.edgeone.run`）。
- `build_offsite_github.py`：组装 GitHub Pages 仓库内容 → `offsite_github/`（已上线 `bistuwangqiyuan.github.io/zk-storage-kb/`）。
- 已上线 URL 记录于 `outputs/offsite_published.json`，并回灌 `site_data.SAMEAS_URLS` → 官网 `Organization.sameAs`（g9）。

## 目录与产物

```
seo_geo_loop/
  levers.py             # 杠杆组定义（g1–g13）+ _geo_levers.json 读写
  readiness_audit.py    # CRI v1/v2 确定性审计（--v2 启用 8 个新子项）
  run_loop.py           # 闭环驱动（默认 v1 10 轮；--v2 等参数跑第二阶段）
  live_audit.py         # 线上收录/排名/技术 SEO 真测
  lighthouse_psi.py     # 线上性能真测（PSI→Playwright 实验室兜底）
  build_offsite_site.py # 站外知识微站（EdgeOne 部署目录）
  build_offsite_github.py # GitHub Pages 仓库内容
  gvi_measure.py        # 真实大模型 GVI 重测与对照
  charts.py             # 苹果风格复现图（matplotlib）
  build_report_html.py  # 苹果视觉 HTML 报告
  export_report_pdf.py  # Playwright A4 PDF
  run.py                # 一键复现编排器
  outputs/
    snapshots/*.json    # 逐轮 CRI 快照（含 v2_round*、final_best_v2）
    loop_results.json / loop_results_v2.json   # 两阶段闭环结果
    changelog.md / changelog_v2.md
    live_status.json / lighthouse.json / offsite_published.json
    gvi_compare.json / gvi_end/raw/**
    figures/*.png
    中科存储-SEO-GEO提升与站外发布报告.html
../中科存储-SEO-GEO提升与站外发布报告.pdf   # 根目录正式 PDF
```

## 复现

```bash
cd seo_geo_loop
python run.py                 # 全流程（两阶段闭环 + 真测 + 站外目录 + 报告）
python run.py --skip-net      # 跳过联网线上真测
python run.py --skip-gvi      # 跳过联网 GVI
# 仅第二阶段（CRI v2，第 11–15 轮）：
python run_loop.py --v2 --from-lever 9 --to-lever 13 --round-offset 2 --suffix _v2
python readiness_audit.py --label check --v2   # 单次 v2 审计当前站点
```

过程无随机、无手绘；GVI 部分为真实 API 采样（原始回答落盘可查）。

## GSC CLI（免浏览器的 Search Console 自动化）

`gsc_cli.py` 用纯标准库（无需 pip）+ Google OAuth 一次性授权，缓存刷新令牌后即可无人值守调用 Search Console API。

```bash
python gsc_cli.py setup-help          # 一次性配置指南（Google Cloud 建 OAuth 桌面客户端）
python gsc_cli.py auth                # 一次性授权（之后免登录）
python gsc_cli.py sites               # 列出已验证属性
python gsc_cli.py sitemaps            # 列出已提交 sitemap
python gsc_cli.py submit-sitemap      # 提交/重提 https://goni.top/sitemap.xml
python gsc_cli.py inspect https://goni.top/zh/product.html   # 单页收录状态（只读）
python gsc_cli.py inspect-batch       # 批量收录状态（默认读线上 sitemap）-> outputs/gsc_inspect_batch.json
python gsc_cli.py analytics --days 28 --dimensions query     # 搜索表现
```

- 凭据与令牌存于 `secrets/`（已 gitignore，绝不入库）；本工具不保存谷歌密码。
- **「请求编入索引」无公开 API**（谷歌仅对 JobPosting/BroadcastEvent 开放 Indexing API），
  该动作只能走浏览器；本仓库其余收录/sitemap/数据查询均可由本 CLI 无浏览器完成。
