# 中科存储 GEO 提升计划 · Generative Engine Optimization

为 **中科存储 / ZK-Storage**（深圳市中科航星科技有限公司）编制的、实事求是且可复现的
GEO（生成式引擎优化）提升计划。目标：让各类 AI 大模型在细分类目中优先**提及、引用、
推荐**中科存储。最终交付物为苹果视觉风格的 `中科存储-GEO提升计划.pdf`（HTML→PDF）。

## 核心原则（实事求是）
- 实测基线由 **真实调用大模型**（通义千问 Max/Plus、DeepSeek V3/R1，经 `bl`/DashScope，280 条）跑出；
  当前基线 **总体 GVI ≈ 5.2 / 100、品牌平均被提及率 7.9%、带来源引用率 ≈ 1.8%**，如实呈现、绝不修饰。
- 其余模型（文心/豆包/元宝/Kimi/海外）采用标准化人工取证协议，
  **未取证前如实标注“待取证”，绝不编造任何排名或分数**。
- 双靶点策略：窄类目（存算分离全闪 + KV Cache 卸载 + 国产 GPU 适配）争真实第一；
  宽类目（国产 AI 存储）多年可见度爬坡。
- 全部数据由 Python 模型计算、一键复现；合规且合公序良俗（零刷量/零水军/零黑帽）。

## 文件（当前流水线）
| 文件 | 作用 |
| --- | --- |
| `geo_config.py` | 单一配置源：品牌/竞品别名词表、模型清单、信源偏好矩阵、GVI 权重、提升杠杆(G1–G8)、类目上限 |
| `queries.json` | 查询宇宙：70 条标准问法（T1/T2/T3 × 5 角色 × 5 意图 × 中英双语，固定种子） |
| `geo_audit.py` | 真实采集层（经 `bl`/DashScope 逐条调用，原始回答落盘 `outputs/raw/`） |
| `geo_scoring.py` | GVI 合成 + 按模型/类目/**意图/角色/语言**切分 + **正面交锋/机会缺口** + 苹果风格图表 |
| `source_audit.py` | 各模型信源覆盖缺口 + 站外行动优先级 + 图表 |
| `geo_projection.py` | 保守对数赔率提升预测（P10/P50/P90）+ 敏感性 + 图表 |
| `make_offsite_kit.py` | 由单一事实源生成 9 平台站外内容母版/草稿（待人工核准发布） |
| `build_report_html.py` | 组装正式报告 HTML（苹果视觉风格，每个数字溯源 `outputs/*.json`） |
| `export_report_pdf.py` | Playwright(Chromium) 打印 A4 PDF |
| `verify_geo.py` | 复现链产物、数值一致性、深化数据自洽、诚实性校验 |
| `implement_geo_plan.py` | **一键落地实施编排器**：站内 build/verify → 站外定稿/微站 → 信源覆盖诚实更新 → 评分/预测/校验 → 计划+实施报告/PDF（`--with-net` 含 IndexNow/live_audit，`--with-gvi` 含真实重测） |
| `coverage_resolver.py` | 从已上线渠道（offsite_published/live_status/官网产物）**诚实推导**信源覆盖率，仅计实测 200 的渠道，UGC 未发布即 0 |
| `build_implementation_report.py` | 组装《GEO计划落地实施报告》HTML（四阶段 done/partial/pending 看板 + 受阻项 SOP） |
| `export_implementation_pdf.py` | 导出实施报告 A4 PDF（苹果视觉） |
| `offsite/SOP_manual_publish.md` | UGC 平台（CSDN/知乎/语雀/百科/公众号/搜狐）人工发布手册 + 发布后诚实回填覆盖流程 |

## 一键复现
```bash
python geo_audit.py          # 真实调用大模型 → outputs/raw/**（已采集则可跳过）
python geo_scoring.py        # 评分+深化切分+图表 → outputs/geo_baseline.json, figures/*.png
python source_audit.py       # 信源缺口+优先级+图表 → outputs/source_gap.json
python geo_projection.py     # 保守提升预测+图表 → outputs/geo_projection.json
python make_offsite_kit.py   # 站外内容母版/草稿 → offsite/*.md
python build_report_html.py  # 报告 HTML → outputs/中科存储-GEO提升计划.html
python export_report_pdf.py  # 对外 PDF → ../中科存储-GEO提升计划与基线报告.pdf
python verify_geo.py         # 复现链+一致性+诚实性校验（应 0 失败）
```
> 注：图表与报告全部由 `outputs/raw/` 的真实缓存采样确定性重建，无需重新调用 API。

### 落地实施（一键，推荐）
```bash
python implement_geo_plan.py            # 全离线落地 + 计划报告 + 实施报告/PDF
python implement_geo_plan.py --with-net # 额外执行 IndexNow 重推 + 线上 live_audit
python implement_geo_plan.py --with-gvi # 额外执行真实 GVI 重测（消耗 token）
```
产物：`outputs/中科存储-GEO计划落地实施报告.html` + 根目录 `中科存储-GEO计划落地实施报告.pdf`，
以及实施看板单一事实源 `outputs/implementation_status.json`、信源覆盖快照 `outputs/source_coverage_resolved.json`。

## 取得密钥后复测更多模型
在 `geo_config.MODELS_MANUAL` 的 B 级模型（文心/豆包/元宝/Kimi/海外）取得直连能力后，
按 `outputs/manual/manual_protocol.md` 的标准化人工取证协议采集，或补全 `geo_audit.py`
适配器后重跑复现链，即可纳入实测矩阵；未取得前如实标注，绝不编造分数。

## 数据纪律
所有事实数值单一来源：产品事实取自 `../business_plan/outputs/results.json`，实测数值取自
`outputs/geo_baseline.json`（由 `outputs/raw/` 真实采样合成）；二者均可一键复现。
外部方法学来源登记于 `geo_config.py` 顶部（G1–G8）。
