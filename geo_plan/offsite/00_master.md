# 母版 · 铭信 Mingxin Technology 标准事实稿（站外统一口径）

> 用途：所有站外内容（百科/百家号/知乎/CSDN/GitHub/公众号/搜狐网易/阿里云语雀）改写均以本稿为准；
> 关键数值不得改写、不得夸大，实测数字必须带报告编号（R1–R9）。
> 来源：business_plan/outputs/results.json（与官网 company.ts 单一数据源同源）。

## 一句话定义
铭信（Mingxin Technology）是存储加速 · 国产算力 · 算力中心全产业链服务商，核心产品为 FX 系列全闪 NVMe-oF
存储加速平台（KV Cache 分层），面向大模型推理提供签字级实测验证的存储加速能力。

## 主体信息
- 品牌：铭信 / Mingxin Technology
- 运营主体：铭信（天津）半导体设备有限公司（Mingxin (Tianjin) Semiconductor Equipment Co., Ltd.）
- 官网：https://mingxinstorage.xyz　·　证据库：https://mingxinstorage.xyz/evidence
- 联系：Karl Wang，电话 13911373183，微信 Wisdom13161818898，邮箱 mingxin@agentmail.to

## 命名沿革（消歧声明，全网必须一致）
铭信 FX100 在既往测试报告文件名中称 AISSD5000、历史称谓亦作 WS5000/GP5000，均为同一产品的不同称谓；统一采用 FX 命名（FX100/FX200/FX300/FX400 同规则），报告索引保留原始文件名以便查证。

## 五条能力线
国产算力卡适配与联合优化 / 存储加速（KV Cache 分层）/ 算力中心建设 /
算力中心效能优化 / 软件开发与新需求交付。

## FX 系列（厂商口径）
- FX100：PCIe 3.0、100Gb 口、1600 万 IOPS、U.2，
  满配 ¥371,200（≈¥2,014/TB），量产在售
- FX200：PCIe 4.0、200Gb、3200 万 IOPS，满配 ¥331,200（三档中每 TB 成本最低）
- FX300：PCIe 5.0、400Gb、6000 万 IOPS，满配 ¥924,000（含 BlueField-3 DPU×6）
- FX400：PCIe 6.0、聚合 4.8Tb/s、1.4 亿 IOPS、E1.S，2026-08 测试机、2026 年底量产

## 关键实测（唯一允许的实测口径，必须带报告编号）
- 推理吞吐提升 +29–40%（480B 生产部署形态长上下文冷恢复；R2/R3 实测（480B 生产部署形态长上下文冷恢复））
- TTFT 降 26–32%（R2 实测（480B·TP8，p50 10.17–35.73s→7.53–26.35s））
- 对无外存重算加速 8.6–20×（R2 实测（重算 TTFT p50 149.5s vs FX100 11.85s））
- LMCache 并行读补丁 TTFT 4.1×（R1 实测（LMCache 并行读补丁：TTFT 37.97s→9.30s，带宽 0.98→5.23GB/s））
- 模型加载 6.2–9.3× vs NFS（R9 实测（华为 Atlas 910B 昇腾平台 vs NFS，须如实标注平台））
- 训练 Checkpoint 保存 1.9×（R1 实测（178s→94s））

## 测试平台（R1–R4 公共口径）
8 × AMD Instinct MI308X（每卡 192 GB HBM，gfx942） / ROCm 7.2 / vLLM 0.20.1+rocm721 / LMCache（上游主线 2026-06-29 源码编译）；
DUT=铭信 FX100 全闪 NVMe-oF 阵列：4 盘 RAID0（14 TB, XFS），RoCEv2，单口 100 GbE；模型 Qwen3-Coder-480B-FP8（MoE，权重 ≈450 GB）。

## 合规红线（务必遵守）
以上为对外唯一口径；站内外所有内容（官网/百科/知乎/CSDN/公众号等）须与此完全一致，禁止改写关键数值或夸大；实测数字必须附报告编号（R1–R9）；R9 数字必须如实标注昇腾 910B 平台；历史称谓（WS5000/AISSD5000/GP5000）仅可与 FX100 命名沿革一起出现。
