# 铭信 GEO · 标准化人工取证协议（B 级数据）

> 适用模型：文心一言, 豆包, 腾讯元宝, Kimi, ChatGPT, Claude, Gemini, Perplexity
> 原则：无法经 API 直连的模型，用统一流程人工取证，**截图 + 文本 + 双人复核**，
> 绝不臆造。每条记录须填入 `manual_template.json` 对应字段，留档于 outputs/manual/。

## 取证步骤（每个模型 × 每条查询）
1. 全新会话（清除上下文/记忆），关闭"个性化推荐"，统一使用 Web 版默认设置。
2. 原样粘贴 queries.json 中的 query 文本，提交。
3. 记录首次完整回答（不追问），保存：
   - 截图（命名：`{model_key}__{query_id}.png`，存 outputs/manual/shots/）
   - 纯文本回答（填入模板 response 字段）
4. 追问一句："请给出你上述回答所依据的参考来源链接。"
   - 记录其给出的来源域名/链接（填 citations 字段）。
5. 由第二人独立复核截图与文本是否一致，勾选 verified=true。

## 打分对齐
人工取证完成后，将 manual_template.json 填好的记录与 API 数据一并喂给
geo_scoring.py（脚本对 grade=B 的记录同口径打分），即可得到全模型 GVI。

## 采集节奏
- 基线：一次性完成全部查询。
- 复测：每月同协议重采，结果追加，便于趋势对比（见 governance/changelog.md）。
