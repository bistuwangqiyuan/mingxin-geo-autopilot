# 中科存储 GEO+SEO 提升闭环 · 复盘记录（changelog）

> 生成时间：2026-06-22T18:02:58　范围：official_website 主站双语内容页（zh/ + en/，不含 training 子站与 portal）

> 基线 CRI **69.51** → 最终 CRI **97.01**（总提升 **+27.50**，权重 {'A': 0.25, 'B': 0.2, 'C': 0.2, 'D': 0.2, 'E': 0.15}）


CRI 度量的是**站内真正可控的 GEO+SEO 就绪度**（确定性、可复现），区别于大模型真实嘴上提及率(GVI，见 geo_plan 真测)。


## 逐轮明细

| 轮次 | 本轮启用 | 支柱 | CRI | Δ | A | B | C | D | E | verify |
|---|---|---|---|---|---|---|---|---|---|---|
| 00 | 基线（无新增杠杆） | - | 69.51 | +0.00 | 0.8348 | 0.8333 | 0.5211 | 0.7222 | 0.4737 | OK |
| 01 | Organization 实体富化 | C/E | 74.00 | +4.49 | 0.8348 | 0.8333 | 0.621 | 0.7222 | 0.6403 | OK |
| 02 | WS7000 Product 结构化数据 | C | 74.00 | +0.00 | 0.8348 | 0.8333 | 0.621 | 0.7222 | 0.6403 | OK |
| 03 | 全站 BreadcrumbList | C | 75.48 | +1.48 | 0.8348 | 0.8333 | 0.6947 | 0.7222 | 0.6403 | OK |
| 04 | WebSite SearchAction | C | 77.48 | +2.00 | 0.8348 | 0.8333 | 0.7947 | 0.7222 | 0.6403 | OK |
| 05 | 核心人物 Person 结构化数据 | C/E | 79.48 | +2.00 | 0.8348 | 0.8333 | 0.8947 | 0.7222 | 0.6403 | OK |
| 06 | 抓取/社媒头部富化 | A/E | 85.25 | +5.77 | 0.9656 | 0.8333 | 0.8947 | 0.7222 | 0.807 | OK |
| 07 | 答案优先「速答 · 关键事实」块 | D | 90.07 | +4.82 | 0.9656 | 0.8333 | 0.8947 | 0.963 | 0.807 | OK |
| 08 | llms-full 全站覆盖 + 更新时间戳 | B/E | 95.90 | +5.83 | 0.9656 | 1.0 | 0.8947 | 0.963 | 0.9737 | OK |
| 09 | 真实站外实体锚点 sameAs | C/E | 95.90 | +0.00 | 0.9656 | 1.0 | 0.8947 | 0.963 | 0.9737 | OK |
| 10 | 答案优先块全覆盖（问句式 H2） | D | 96.64 | +0.74 | 0.9656 | 1.0 | 0.8947 | 1.0 | 0.9737 | OK |

## 每个杠杆组的真实改进内容

- **Organization 实体富化**（g1_org，支柱 C/E）：为全站 Organization 结构化数据补 slogan/brand/knowsAbout/contactPoint/numberOfEmployees/areaServed 等可核验字段（不臆造外部 sameAs 档案）。
- **WS7000 Product 结构化数据**（g2_product，支柱 C）：在 AI 算力中心方案页为 WS7000 平台补 Product schema（规格为项目方口径，如实标注）。
- **全站 BreadcrumbList**（g3_breadcrumb，支柱 C）：为全部主站内容页自动补 BreadcrumbList（此前仅 GEO 专题页具备）。
- **WebSite SearchAction**（g4_search，支柱 C）：为 WebSite 结构化数据补 potentialAction(SearchAction)，暴露站内检索入口。
- **核心人物 Person 结构化数据**（g5_person，支柱 C/E）：在关于我们页补 CEO / 首席科学家 / 院士顾问的 Person schema（真实身份）。
- **抓取/社媒头部富化**（g6_headmeta，支柱 A/E）：补 theme-color、og:locale:alternate、twitter:title/description、author/publisher、generator 与 robots max-snippet 等头部信号。
- **答案优先「速答 · 关键事实」块**（g7_answer，支柱 D）：在产品/技术/实测/解决方案/AI算力中心页注入问句式 H2 + 自足直答 + 可核验来源的关键事实块。
- **llms-full 全站覆盖 + 更新时间戳**（g8_llms，支柱 B/E）：llms-full.txt 增列全站页面索引；每页加可见的机器可读「最后更新」<time>。
- **真实站外实体锚点 sameAs**（g9_sameas，支柱 C/E）：把已上线且实测可达的站外信源（EdgeOne 知识微站 + GitHub Pages/仓库）注入 Organization.sameAs；仅写真实 URL，兑现此前诚实留空的实体锚点。
- **答案优先块全覆盖（问句式 H2）**（g10_answer_all，支柱 D）：把「速答·关键事实」答案块 + 问句式 H2 扩展到 faq/glossary/ip/about/cases 等剩余主内容页，提升问句式 H2 覆盖率与可抽取直答比例。
- **全站规格口径一致性**（g11_spec_consistency，支柱 E）：审计驱动地统一全站关键规格表述（带宽/IOPS/时延/适配/中位降幅等），消除口径漂移，强化实体一致性与 E-E-A-T。
- **媒体尺寸 + Speakable + WebPage**（g12_media_speakable，支柱 A/C）：为正文图补 width/height + loading=lazy + decoding=async（降 CLS）；首页注入 WebPage 与 SpeakableSpecification，便于语音/抽取式呈现。
- **性能就绪（font-display + preload）**（g13_perf，支柱 A）：关键 CSS 预加载、font-display:swap、消除渲染阻塞冗余；静态「性能就绪」子项并入 CRI v2，真实 Lighthouse/实验室分另列作线上验证。

## 收敛与自我批评

- 杠杆全开后 CRI 收敛于 **97.01**（结构上限，非人为 100）。
- 仍未满分的子项（如实记录，留待站外执行/后续迭代）：
  - C.product = 0.0
  - E.spec_consistency = 0.9474

> 复现：`python run_loop.py` —— 过程无随机、无网络，任何人可逐轮复算。
