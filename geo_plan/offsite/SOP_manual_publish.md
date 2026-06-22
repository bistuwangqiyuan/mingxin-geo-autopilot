# -*- coding: utf-8 -*-
"""站外 UGC 平台人工发布 SOP（白帽 · 实事求是）

> 本文件为 GEO 提升计划阶段二/三的**可执行人工操作手册**。
> 定稿位于 `geo_plan/offsite/*.md`；**禁止**自动发帖、刷量、伪造测评。

## 通用发布前核对（每篇必做）

1. 打开 `geo_plan/offsite/publish_checklist.md`，逐项勾选。
2. 运行一致性抽检（可选）：
   ```bash
   cd geo_plan
   python -c "from source_audit import entity_facts, check_consistency; import pathlib; f=entity_facts(); t=pathlib.Path('offsite/csdn.md').read_text(encoding='utf-8'); print(check_consistency(t,f) or 'OK')"
   ```
3. 确认含官网链接 `https://goni.top` 及对应专题页 deep link。
4. 发布后记录 live URL 到 `geo_plan/outputs/published_urls.json`（新建），供下次 `coverage_resolver` 诚实计分。

---

## 阶段二 · DeepSeek / 通义信源（第 3–6 周）

### CSDN（影响 DeepSeek / Kimi）· 定稿 `csdn.md`

1. 登录 [CSDN 创作中心](https://mp.csdn.net/)（需实名）。
2. 新建「原创」技术文章；标题与定稿 H1 一致。
3. 正文粘贴 `csdn.md` 内容；保留 Markdown 表格与代码块。
4. 标签建议：`KV Cache` `全闪存储` `存算分离` `AI推理` `中科存储`。
5. 发布前预览 → 发布 → 复制文章 URL。
6. 在评论区置顶一条：「官方站点 https://goni.top · 知识库 https://bistuwangqiyuan.github.io/zk-storage-kb/」。

### 知乎技术区（影响 DeepSeek）· 定稿 `zhihu.md`

1. 登录知乎 → 创作 → 写回答或专栏文章（专栏需开通）。
2. 选择高相关问题（如「KV Cache 卸载 存储方案」「存算分离全闪存储推荐」）或发专栏。
3. 粘贴 `zhihu.md`；首段 120 字内给出可摘录结论。
4. 文末附官网与 GitHub Pages 链接。
5. 发布后记录 URL。

### 阿里云开发者社区 / 语雀（影响通义千问）· 定稿 `aliyun_yuque.md`

**语雀：**
1. 登录语雀 → 新建公开知识库「中科存储 GEO 知识库」。
2. 按定稿章节拆分为 3–5 篇文档；每篇含 FAQ 式 H2。
3. 设置知识库为公开 → 复制首页 URL。

**阿里云开发者社区：**
1. 登录 [阿里云开发者社区](https://developer.aliyun.com/) → 发布文章。
2. 使用强结构化标题（H2/H3）、数据模块、FAQ 块（通义偏好）。
3. 文末附官网链接。

### GitHub README（影响 DeepSeek）· 定稿 `github_readme.md`

**已自动化：** `seo_geo_loop/build_offsite_github.py` 同步至 `offsite_github/README.md`。
手动步骤（若需更新远程）：
```bash
cd offsite_github
git add README.md docs/
git commit -m "docs: refresh GEO knowledge base README"
git push origin main
```

---

## 阶段三 · 文心 / 豆包 / 元宝 / Kimi（第 7–14 周）

| 平台 | 定稿 | 操作要点 |
|------|------|----------|
| 百度百科 | `baike_baidu.md` | 需企业资质或权威来源；中性百科口径；引用第三方实测 |
| 百家号 | `baijiahao.md` | 蓝 V 企业号；资讯口径；来源支撑 |
| 微信公众号 | `wechat_mp.md` | 深度科普；关键数字加粗；文末官网链接 |
| 搜狐/网易 | `sohu_163.md` | 资讯流；信息前置可摘录 |

---

## 阶段四 · 实体锚点 sameAs

**纪律：** 仅当外部档案**已上线且实测 HTTP 200** 后，才写入 `official_website/site_data.py` → `OFFSITE_LINKS`。

当前已写入（2026-06-22）：
- EdgeOne 知识微站
- GitHub Pages 知识库
- GitHub 仓库

待办（发布后执行）：
1. 将 live URL 追加到 `OFFSITE_LINKS`。
2. `python official_website/build_site.py && python verify_site.py`
3. `git commit && git push` 触发 Netlify 部署。

---

## B 级模型人工取证（文心/豆包/元宝/Kimi/海外）

协议：`geo_plan/outputs/manual/manual_protocol.md`
模板：`geo_plan/outputs/manual/manual_template.json`

1. 按协议对 70 问法逐条提问并截图。
2. 双人复核后填入 `outputs/manual/shots/`。
3. 汇总后运行 `geo_scoring.py` 纳入 B 级矩阵（待适配器补全）。

---

## 发布后更新信源覆盖（诚实计分）

1. 将 live URL 写入 `geo_plan/outputs/published_urls.json`：
   ```json
   {"CSDN": "https://...", "知乎技术区": "https://...", ...}
   ```
2. 更新 `coverage_resolver.py` 或 `geo_config.CURRENT_SOURCE_COVERAGE`（仅对已验证 URL 加分）。
3. 重跑：`python source_audit.py && python build_implementation_report.py`
