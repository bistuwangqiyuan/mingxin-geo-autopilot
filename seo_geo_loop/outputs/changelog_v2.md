# 中科存储 GEO+SEO 第二阶段 · CRI v2 复盘（changelog）

> 生成：2026-06-22T18:03:11　范围：official_website 主站双语内容页（zh/ + en/，不含 training 子站与 portal）

> 阶段基线 CRI v2 **86.33** → 最终 CRI v2 **96.44**（Δ **+10.11**）；同口径 CRI v1 终值 **97.01**（突破第一阶段 97.9 上限）。


## 逐轮明细（CRI v2）

| 轮次 | 本轮启用 | 支柱 | CRI v2 | Δ | A | B | C | D | E | verify |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 阶段基线（g1–g8） | - | 86.33 | +0.00 | 0.8568 | 1.0 | 0.7456 | 0.878 | 0.8289 | OK |
| 11 | 真实站外实体锚点 sameAs | C/E | 89.87 | +3.54 | 0.8568 | 1.0 | 0.8289 | 0.878 | 0.9539 | OK |
| 12 | 答案优先块全覆盖（问句式 H2） | D | 91.25 | +1.38 | 0.8568 | 1.0 | 0.8289 | 0.9474 | 0.9539 | OK |
| 13 | 全站规格口径一致性 | E | 91.85 | +0.60 | 0.8568 | 1.0 | 0.8289 | 0.9474 | 0.9934 | OK |
| 14 | 媒体尺寸 + Speakable + WebPage | A/C | 95.02 | +3.17 | 0.9135 | 1.0 | 0.9167 | 0.9474 | 0.9934 | OK |
| 15 | 性能就绪（font-display + preload） | A | 96.44 | +1.42 | 0.9702 | 1.0 | 0.9167 | 0.9474 | 0.9934 | OK |

## 新增 5 个杠杆组的真实改进内容

- **真实站外实体锚点 sameAs**（g9_sameas，支柱 C/E）：把已上线且实测可达的站外信源（EdgeOne 知识微站 + GitHub Pages/仓库）注入 Organization.sameAs；仅写真实 URL，兑现此前诚实留空的实体锚点。
- **答案优先块全覆盖（问句式 H2）**（g10_answer_all，支柱 D）：把「速答·关键事实」答案块 + 问句式 H2 扩展到 faq/glossary/ip/about/cases 等剩余主内容页，提升问句式 H2 覆盖率与可抽取直答比例。
- **全站规格口径一致性**（g11_spec_consistency，支柱 E）：审计驱动地统一全站关键规格表述（带宽/IOPS/时延/适配/中位降幅等），消除口径漂移，强化实体一致性与 E-E-A-T。
- **媒体尺寸 + Speakable + WebPage**（g12_media_speakable，支柱 A/C）：为正文图补 width/height + loading=lazy + decoding=async（降 CLS）；首页注入 WebPage 与 SpeakableSpecification，便于语音/抽取式呈现。
- **性能就绪（font-display + preload）**（g13_perf，支柱 A）：关键 CSS 预加载、font-display:swap、消除渲染阻塞冗余；静态「性能就绪」子项并入 CRI v2，真实 Lighthouse/实验室分另列作线上验证。

## 收敛与自我批评

- 全开后 CRI v2 收敛于 **96.44**、CRI v1 收敛于 **97.01**。
- 仍未满分的 v2 子项（如实记录）：
  - C.product = 0.0
  - D.answer_all = 0.6316
  - E.spec_consistency = 0.9474

> 复现：`python run_loop.py --v2 --from-lever 9 --to-lever 13 --round-offset 2 --suffix _v2`

---

## 2026-06-22 · 全量重跑闭环 + 真实上线（rerun，本节为手工留痕，非自动生成）

本轮按授权执行"全量重跑 + 全授权实时动作"，全程实事求是、受阻如实记录：

- **站内闭环**：`run_loop.py --rounds 10`（CRI 69.51→97.01）+ `--v2`（86.33→96.44），verify 全 OK，`official_website` 重建至最佳态（确定性、可复现）。
- **站外重建+上线**：`build_offsite_site.py` / `build_offsite_github.py` 重建；EdgeOne 微站经 MCP 重新部署至新子域 `manju-studio-dpvdtbb7pu7a.edgeone.run`（实测 200，含 JSON-LD）；GitHub Pages 推送 `commit fc98c43`（实测 200）。
- **官网部署**：本地 `main` 与 `origin/main` 一致（最佳构建已在线）；将 `Organization.sameAs` 回灌为最新 EdgeOne 子域后重建并推送 `commit dd58cc5`，触发 Netlify 重新部署；关键页/sitemap/robots/IndexNow key 文件实测 200。
- **IndexNow**：重推 68 条 URL（Bing 200、Yandex 202；Google/Bing ping 接口已被官方弃用，如实记录）。
- **线上真测**：`live_audit.py` 复核线上 HTML（首页 4 段 JSON-LD、会话级升级在线）；`lighthouse_psi.py` 因 PSI 配额 429 退回 Playwright 实验室（首页 LCP≈4.4s/FCP≈3.3s，已标注 method=lab）。
- **真实 SERP（2026-06-22 agent web_search）**：`site:goni.top` 公开检索仍零结果；目标词头部全部为中科曙光 FlashNexus/ParaStor，goni.top 未进榜，品牌混淆风险持续且强烈（模型甚至误判"中科曙光未发布 WS5000"）。
- **GSC**：当日"请求编入索引"配额已于 00:15 用尽（6 成功 + 第 7 次超额），且浏览器 GSC 会话正用于另一属性（sc-domain:zoka.top）；为不打断用户会话且配额已耗，本轮未重复请求，pending 顺延次日（详见 `live_status.gsc_url_inspection.rerun_note`）。
- **真实 GVI 重测**（4 模型 × 70 查询 × 真 API，`--force` 全量重采，原始回答落盘 `outputs/gvi_end/raw/`）：**GVI 5.21（n=280）→ 5.01（n=277），Δ−0.20**，落在采样噪声内。诚实结论：站内优化不改变模型语料，真实 GVI 阶跃需站外多信源随时间被收录/引用——这正是本轮夯实站外信源与实体网络的意义。
- **报告与 PDF**：`charts.py`（9 图）→ `build_report_html.py` → `export_report_pdf.py`，产出根目录 `中科存储-SEO-GEO提升与站外发布报告.pdf`（1.41 MB，A4 苹果视觉）。
- **版本控制说明**：仓库根 `microai` 非 git 仓库；受版本控制的 `official_website`(dd58cc5) 与 `zk-storage-kb`(fc98c43) 均已提交并推送，`seo_geo_loop/outputs` 为本地交付产物。

> 红线遵守：UGC 平台无开放写 API/需实名 → 不自动发帖，仅交付定稿 + SOP；预测一律标注"规划假设、非承诺"；sameAs 仅写实测 200 的 URL；不刷量、不伪造、不隐藏文字。

---

## 2026-06-23 · 全自动 AI GEO 系统（GEO Autopilot）开发 + 本地端到端测试（本节手工留痕）

新建 `geo_autopilot/`：一套云端每日无人值守、全 AI 驱动的官网 GEO 系统，开发完成并本地端到端跑通。

- **架构**：`autopilot.py` 统一编排（`--dry-run/--once/--ci` + `--gvi-limit/--skip-gvi/--no-llm` 预算超时护栏），`paths.py` 环境自适应解析引擎与站点路径。
- **AI 决策脑**（`geo_brain.py`）：把当日真实指标喂给 `qwen-max`（经 bl `--messages-file`/`--output json`），产出结构化 JSON 决策（优先级 + 批评与自我批评 + 内容提案）；LLM 不可达时回退确定性规则脑并如实标注 `engine`。**实测 `engine=llm:qwen-max` 正常产出 2 优先级 / 2 提案 / 2 自我批评。**
- **内容自进化**（`apply_proposals.py`）：AI 提案先过「事实口径一致性闸门」（复用 `source_audit.check_consistency`）再过 `verify_site.py` 构建闸门，失败自动回滚。**实测：接受 1 条带 300 GB/s & 20 μs 的 FAQ（口径一致）并通过 verify 上线；注入 999 GB/s / 1 μs 的伪造数值被准确拦截（自我净化生效）。** `build_site.py` 新增可选 `autopilot_faq.json` 附加读取（仅附加、不覆盖单一事实源）。
- **历史/趋势/日报**：`metrics.py`（快照）+ `trend.py`（苹果风趋势图）+ `build_daily_report.py`/`export_daily_pdf.py`（《GEO 自动驾驶日报》A4 PDF，5 页 / 331 KB，实测渲染良好）。
- **告警**（`alerting.py`）：回归/部署失败/verify 失败/待人工项 → 经 `gh` 开/更新固定标题 Issue（含数据快照 + SOP），无 gh/无权限则本地落盘不阻断。实测 `level=warn`（由 GSC/UGC/ICP 人工项驱动，无伪造完成）。
- **云端 cron**：`.github/workflows/geo-autopilot.yml`（每日 cron + workflow_dispatch；装 Python/Node/Playwright/bailian-cli → clone 官网/知识库 → `autopilot.py --ci` → 推站点 + 提交 autopilot 数据 + 上传日报 artifact）。
- **自治仓库装配**（`make_repo.py`）：把最小引擎（geo_autopilot + geo_plan + seo_geo_loop + results.json）装配成可推送的 `zk-geo-autopilot`，workflow 提升到仓库根 `.github/`。**已本地 git init + commit；安全扫描确认无 API Key / OAuth 令牌泄露。**
- **本地端到端实测**：`autopilot.py --dry-run`（10/10 步 OK）；`--once --skip-gvi`（20/20 步 OK，0 关键失败，37.7s）含真实 IndexNow 重推 72 URL、`live_audit` 线上核验、官网/知识库本地提交（未 push）。

> 诚实边界（不伪造、已在系统内固化）：GSC 请求收录（需登录/配额/无写 API）、UGC 发布（无开放写 API/需实名）、百度收录（需 ICP）→ 系统自动开 Issue + 给 SOP，绝不自动伪装完成。
>
> 上线唯一需人工的一次性环节（见 `geo_autopilot/SETUP.md`）：`gh repo create` 推送 → 配置仓库 Secrets（`DASHSCOPE_API_KEY`、细粒度 `GH_PAT`）→ `workflow_dispatch` 首跑 → cron 接管。系统从不打印/提交任何密钥。
