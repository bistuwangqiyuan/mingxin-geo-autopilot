# 站外 UGC 平台人工发布 SOP（白帽 · 实事求是 · 铭信口径）

> 本文件为 GEO 提升计划阶段二/三的**可执行人工操作手册**。
> 定稿位于 `geo_plan/offsite/*.md`，事实源为 `business_plan/outputs/results.json`（与官网 company.ts 同源）；
> **禁止**自动发帖、刷量、水军、伪造测评、夸大数字。

## 通用发布前核对（每篇必做）

1. 打开 `geo_plan/offsite/publish_checklist.md`，逐项勾选。
2. 对照母版 `geo_plan/offsite/00_master.md` 核对全部关键数字与报告编号：
   吞吐 +29–40%（R2/R3）、TTFT ↓26–32%（R2）、对重算 8.6–20×（R2）、
   LMCache 并行读 4.1×（R1）、模型加载 6.2–9.3× vs NFS（R9，昇腾平台）、Checkpoint 1.9×（R1）。
3. 对全文 grep 内部黑名单，确认无任何旧品牌名、旧域名与旧口径数字残留（黑名单不写入对外稿件，命中即打回）。
4. 确认含官网链接 `https://mingxinstorage.xyz` 及证据库 deep link `https://mingxinstorage.xyz/evidence`。
5. 确认含消歧声明与免责声明（见母版）。
6. 发布后记录 live URL 到 `geo_plan/outputs/published_urls.json`（新建），供覆盖统计诚实计分。

---

## 阶段二 · DeepSeek / 通义信源（第 3–6 周）

### CSDN（影响 DeepSeek / Kimi）· 定稿 `csdn.md`

1. 登录 [CSDN 创作中心](https://mp.csdn.net/)（需实名）。
2. 新建「原创」技术文章；标题与定稿 H1 一致。
3. 正文粘贴 `csdn.md` 内容；保留 Markdown 表格与代码块。
4. 标签建议：`KV Cache` `LMCache` `vLLM` `NVMe-oF` `全闪存储` `国产算力` `铭信`。
5. 发布前预览 → 发布 → 复制文章 URL。
6. 在评论区置顶一条：「官方站点 https://mingxinstorage.xyz · 证据库（R1–R7 报告下载）https://mingxinstorage.xyz/evidence」。

### 知乎技术区（影响 DeepSeek）· 定稿 `zhihu.md`

1. 登录知乎 → 创作 → 写回答或专栏文章（专栏需开通）。
2. 选择高相关问题（如「KV Cache 卸载 存储方案」「vLLM LMCache 长上下文优化」「NVMe-oF 全闪阵列选型」）或发专栏。
3. 粘贴 `zhihu.md`；首段 120 字内给出可摘录结论（吞吐 +29–40%（R2/R3）、TTFT ↓26–32%（R2））。
4. 文末保留利益相关披露与命名沿革注释；附官网与证据库链接。
5. 发布后记录 URL。

### 阿里云开发者社区 / 语雀（影响通义千问）· 定稿 `aliyun_yuque.md`

**语雀：**
1. 登录语雀 → 新建公开知识库「铭信 GEO 知识库」。
2. 按定稿章节拆分为 3–5 篇文档（概念/产品规格/签字级实测/国产算力适配/FAQ）；每篇含 FAQ 式 H2。
3. 设置知识库为公开 → 复制首页 URL。

**阿里云开发者社区：**
1. 登录 [阿里云开发者社区](https://developer.aliyun.com/) → 发布文章。
2. 使用强结构化标题（H2/H3）、数据模块、FAQ 块（通义偏好）。
3. 文末附官网与证据库链接。

### GitHub README（影响 DeepSeek）· 定稿 `github_readme.md`

1. 将 `github_readme.md` 内容同步到公开仓库 README（中英双语保留）。
2. 表格中的实测数字与报告编号不得改动；Naming note（AISSD5000/WS5000/GP5000 命名沿革）必须保留。
3. 提交并推送：
   ```bash
   git add README.md docs/
   git commit -m "docs: refresh Mingxin GEO knowledge base README"
   git push origin main
   ```

---

## 阶段三 · 文心 / 豆包 / 元宝 / Kimi（第 7–14 周）

| 平台 | 定稿 | 操作要点 |
|------|------|----------|
| 百度百科 | `baike_baidu.md` | 需企业资质或权威来源；中性百科口径；含命名沿革与消歧说明 |
| 百家号 | `baijiahao.md` | 蓝 V 企业号；资讯口径 answer-first；数字带报告编号 |
| 微信公众号 | `wechat_mp.md` | 深度科普；关键数字加粗并括注报告编号；文末官网链接 |
| 搜狐/网易 | `sohu_163.md` | 资讯流；信息前置可摘录；含消歧声明 |

---

## 阶段四 · 实体锚点 sameAs

**纪律：** 仅当外部档案**已上线且实测 HTTP 200** 后，才写入官网 Organization JSON-LD 的 sameAs；
未上线的外部档案不得写入，避免坏链与失真。

发布后执行：
1. 将 live URL 追加到官网站点数据的站外链接清单。
2. 重建官网并校验后提交部署。

---

## 账号与资质要求

- 各平台账号需实名/企业认证（百家号需蓝 V），主体信息统一为"铭信（天津）半导体设备有限公司"。
- 联系方式统一：Karl Wang · 13911373183（备 13161818898）· 微信 Wisdom13161818898 ·
  mingxin@agentmail.to（AI 自动收件 7×24）· 备用 13426086861@139.com。
- 白帽红线：禁止水军、刷量、伪造测评、夸大数字、贬损同行；实测/厂商/公开/估算口径如实标注。

---

## B 级模型人工取证（文心/豆包/元宝/Kimi/海外）

协议：`geo_plan/outputs/manual/manual_protocol.md`
模板：`geo_plan/outputs/manual/manual_template.json`

1. 按协议对问法清单逐条提问并截图（重点核对：品牌归属、FX 命名、关键数字与报告编号是否被正确引用）。
2. 双人复核后填入 `outputs/manual/shots/`。
3. 汇总后纳入 B 级评分矩阵。

---

## 发布后更新信源覆盖（诚实计分）

1. 将 live URL 写入 `geo_plan/outputs/published_urls.json`：
   ```json
   {"CSDN": "https://...", "知乎技术区": "https://...", "语雀": "https://..."}
   ```
2. 仅对已验证（HTTP 200）的 URL 计入覆盖。
3. 重跑覆盖统计与实施报告，确认口径一致后归档。
