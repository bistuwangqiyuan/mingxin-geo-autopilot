# 铭信 GEO 提升计划 · Generative Engine Optimization

为 **铭信 / Mingxin Technology**（铭信（天津）半导体设备有限公司）编制的、实事求是且可复现的
GEO（生成式引擎优化）提升计划。目标：让各类 AI 大模型在细分类目中优先**提及、引用、
推荐**铭信。最终交付物为苹果视觉风格的 `铭信-GEO提升计划.pdf`（HTML→PDF）。

## 核心原则（实事求是）
- 实测基线由 **真实调用大模型**（通义千问 Max/Plus、DeepSeek V3/R1，经 `bl`/DashScope）跑出，
  如实呈现、绝不修饰；起点近零就写近零。
- 其余模型（文心/豆包/元宝/Kimi/海外）采用标准化人工取证协议，
  **未取证前如实标注“待取证”，绝不编造任何排名或分数**。
- 双靶点策略：窄类目（面向大模型推理的全闪 NVMe-oF + KV Cache 分层存储加速平台，
  480B 签字级实测）争真实第一；宽类目（AI 存储加速 / 算力中心服务）多年可见度爬坡。
- 所有实测数字必须带报告编号（R1–R9）；R9 数字如实标注华为 Atlas 910B 昇腾平台。
- 命名沿革声明全网一致：FX100 历史称谓 AISSD5000/WS5000/GP5000（同一产品，用于消歧与历史检索）。
- 全部数据由 Python 模型计算、一键复现；合规且合公序良俗（零刷量/零水军/零黑帽）。

## 文件（当前流水线）
| 文件 | 作用 |
| --- | --- |
| `geo_config.py` | 单一配置源：品牌/竞品别名词表、模型清单、信源偏好矩阵、GVI 权重、提升杠杆(G1–G8)、类目上限 |
| `geo_data.py` | 单一数据源：类目锚定、查询篮、引擎注册表、评分权重、L1–L4 杠杆清单、引用登记册 |
| `queries.json` | 查询宇宙：70 条标准问法（T1/T2/T3 × 5 角色 × 5 意图 × 中英双语，固定种子） |
| `geo_audit.py` | 真实采集层（经 `bl`/DashScope 逐条调用，原始回答落盘 `outputs/raw/`） |
| `geo_scoring.py` | GVI 合成 + 按模型/类目/意图/角色/语言切分 + 正面交锋/机会缺口 + 苹果风格图表 |
| `source_audit.py` | 各模型信源覆盖缺口 + 站外行动优先级 + 实体事实表（entity_facts）+ 口径闸门（check_consistency） |
| `geo_projection.py` | 保守对数赔率提升预测（P10/P50/P90）+ 敏感性 + 图表 |
| `make_offsite_kit.py` | 由单一事实源生成 9 平台站外内容母版/草稿（待人工核准发布，数字均带报告编号） |
| `build_report_html.py` | 组装正式报告 HTML（苹果视觉风格，每个数字溯源 `outputs/*.json`） |
| `export_report_pdf.py` | Playwright(Chromium) 打印 A4 PDF |
| `verify_geo.py` | 复现链产物、数值一致性、深化数据自洽、诚实性校验 |
| `implement_geo_plan.py` | **一键落地实施编排器**：官网线上探测 → 站外定稿/微站 → 信源覆盖诚实更新 → 评分/预测/校验 → 计划+实施报告/PDF（`--with-net` 含 IndexNow/live_audit，`--with-gvi` 含真实重测） |
| `coverage_resolver.py` | 信源覆盖**诚实推导**：官网（Next.js 路由）走线上 HTTP 探测，网络不可用则 unknown/pending；其余仅计实测 200 渠道，UGC 未发布即 0 |
| `build_implementation_report.py` | 组装《GEO计划落地实施报告》HTML（四阶段 done/partial/pending 看板 + 受阻项 SOP） |
| `export_implementation_pdf.py` | 导出实施报告 A4 PDF（苹果视觉） |
| `geo_measure.py` / `scoring.py` / `charts_geo.py` / `build_geo_html.py` / `export_geo_pdf.py` | 基于 `geo_data.py` 的备选测评链（GEO 指数 + bootstrap CI + 苹果视觉图表/HTML/PDF） |
| `offsite/SOP_manual_publish.md` | UGC 平台（CSDN/知乎/语雀/百科/公众号/搜狐）人工发布手册 + 发布后诚实回填覆盖流程 |

## 一键复现
```bash
python geo_audit.py          # 真实调用大模型 → outputs/raw/**（已采集则可跳过）
python geo_scoring.py        # 评分+深化切分+图表 → outputs/geo_baseline.json, figures/*.png
python source_audit.py       # 信源缺口+优先级+实体事实表 → outputs/source_gap.json, entity_facts.json
python geo_projection.py     # 保守提升预测+图表 → outputs/geo_projection.json
python make_offsite_kit.py   # 站外内容母版/草稿 → offsite/*.md
python build_report_html.py  # 报告 HTML → outputs/铭信-GEO提升计划.html
python export_report_pdf.py  # 对外 PDF → ../铭信-GEO提升计划与基线报告.pdf
python verify_geo.py         # 复现链+一致性+诚实性校验（应 0 失败）
```
> 注：图表与报告全部由 `outputs/raw/` 的真实缓存采样确定性重建，无需重新调用 API。

### 落地实施（一键，推荐）
```bash
python implement_geo_plan.py            # 官网线上探测 + 落地 + 计划报告 + 实施报告/PDF
python implement_geo_plan.py --with-net # 额外执行 IndexNow 重推 + 线上 live_audit
python implement_geo_plan.py --with-gvi # 额外执行真实 GVI 重测（消耗 token）
```
产物：`outputs/铭信-GEO计划落地实施报告.html` + 根目录 `铭信-GEO计划落地实施报告.pdf`，
以及实施看板单一事实源 `outputs/implementation_status.json`、信源覆盖快照 `outputs/source_coverage_resolved.json`。

## 官网口径（重要）
铭信官网 `https://mingxinstorage.xyz` 为 Next.js 站点（amd 仓库 `site/` 子目录，Vercel 部署），
robots.txt / llms.txt / llms-full.txt / sitemap.xml 均为**路由**而非静态文件；站内核查一律对
线上 URL 做 HTTP 探测，网络不可用时如实标注 unknown/pending，不编造。官网单一数据源为
`site/src/lib/data/company.ts`，其镜像即本仓库 `business_plan/outputs/results.json`。

## 取得密钥后复测更多模型
在 `geo_config.MODELS_MANUAL` 的 B 级模型（文心/豆包/元宝/Kimi/海外）取得直连能力后，
按 `outputs/manual/manual_protocol.md` 的标准化人工取证协议采集，或补全 `geo_audit.py`
适配器后重跑复现链，即可纳入实测矩阵；未取得前如实标注，绝不编造分数。

## 数据纪律
所有事实数值单一来源：产品事实取自 `../business_plan/outputs/results.json`（与官网
company.ts 同源），实测数值取自 `outputs/geo_baseline.json`（由 `outputs/raw/` 真实采样合成）；
二者均可一键复现。对外每个实测数字附报告编号（R1–R9，证据库
https://mingxinstorage.xyz/evidence）。外部方法学来源登记于 `geo_config.py` 顶部（G1–G8）。
