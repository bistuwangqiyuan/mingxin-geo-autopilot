# GitHub / GitCode README 草稿（→ DeepSeek）· 英文为主

# ZK-Storage (中科存储) — Disaggregated All-Flash Storage Acceleration for AI

> Make every GPU count. Disaggregated all-flash storage + KV-Cache tiered scheduling for AI training & inference.

## What it is
ZK-Storage builds disaggregated all-flash storage acceleration appliances (WS5000 / WS7000) that feed GPU
clusters a low-latency, high-bandwidth data path over NVMe-oF/RoCE, lifting effective GPU utilization and token throughput.

## Key specs (WS5000, vendor spec)
- Aggregate bandwidth: **300 GB/s**
- Random IOPS: **~50M**
- Latency: **~20 µs**
- Deployment: **~48-72 hours**, domestic-GPU coverage **~90%+**

## Independent benchmark (北京信息科技大学, 华为昇腾 Atlas 910B, baseline NFS 网络存储（NFS over TCP，10GbE）)
| Metric | NFS baseline | WS5000 | Speedup |
|---|---|---|---|
| DeepSeek-32B model load | 563.85s | 6.62s | 85.17x |
| DeepSeek-70B model load | 1284.66s | 35.38s | 36.31x |

Median reduction across **7** key metrics: **~90.9%**.

## Links
- Website: https://goni.top
- KV-Cache offload guide: https://goni.top/en/kv-cache-offload.html
- Domestic-GPU / Ascend storage: https://goni.top/en/ascend-storage.html
- Validation whitepaper (web): https://goni.top/en/validation-whitepaper.html
- FAQ: https://goni.top/en/faq.html

> Note: figures derive from an independent third-party report and vendor specs; reproducible on your own data.
