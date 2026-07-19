# -*- coding: utf-8 -*-
"""铭信 GEO · 多厂商 LLM 统一调用层（纯 stdlib urllib，OpenAI 兼容优先）。

一处注册、处处复用：GVI 多模型实测（geo_measure）、AI 决策脑（geo_brain）、
热词挖掘（keyword_miner）共用本层，实现 24h 全自动多模型运行。

支持引擎（密钥存在即视为可实测；调用失败如实记录 error，绝不编造）：
  tongyi(通义/DashScope 兼容模式)  deepseek  glm(智谱)  kimi(月之暗面)
  hunyuan(腾讯混元)  spark(讯飞星火)  doubao(火山方舟)  claude(Anthropic)  gemini(Google)

纪律：
  - 密钥只从环境变量读取（CI 用 GitHub Secrets 注入；本地可在仓库根 .env——已 gitignore）。
  - 本模块绝不打印/落盘任何密钥。
  - 每家模型名可用 MX_<PROVIDER>_MODEL 环境变量覆盖（如 MX_GLM_MODEL=glm-4-air）。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_BASE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BASE)


def _load_dotenv():
    """加载仓库根 .env（KEY=VALUE 简单格式），不覆盖已存在的环境变量。"""
    p = os.path.join(_ROOT, ".env")
    if not os.path.isfile(p):
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


_load_dotenv()

# ---------------------------------------------------------------------------
# 厂商注册表。env_keys 依序取第一个存在的环境变量（兼容用户提供的历史命名）。
# ---------------------------------------------------------------------------
PROVIDERS = {
    "tongyi": {
        "label": "通义千问 (DashScope)", "vendor": "阿里巴巴", "style": "openai",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
        "env_keys": ["TONGYI_API_KEY", "DASHSCOPE_API_KEY"],
    },
    "deepseek": {
        "label": "DeepSeek", "vendor": "深度求索", "style": "openai",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_keys": ["DEEPSEEK_API_KEY"],
    },
    "glm": {
        "label": "智谱 GLM", "vendor": "智谱 AI", "style": "openai",
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4.5",
        "env_keys": ["GLM_API_KEY", "ZHIPU_API_KEY"],
    },
    "kimi": {
        "label": "Kimi (Moonshot)", "vendor": "月之暗面", "style": "openai",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "model": "moonshot-v1-8k",
        "env_keys": ["MOONSHOT_API_KEY", "KIMI_API_KEY"],
    },
    "hunyuan": {
        "label": "腾讯混元 (元宝)", "vendor": "腾讯", "style": "openai",
        "url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
        "model": "hunyuan-turbos-latest",
        "env_keys": ["HUNYUAN_API_KEY", "TENCENT_API_KEY", "TENGCENT_API_KEY"],
    },
    "spark": {
        "label": "讯飞星火", "vendor": "科大讯飞", "style": "openai",
        "url": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "generalv3.5",
        "env_keys": ["SPARK_API_KEY"],
    },
    "doubao": {
        "label": "豆包 (方舟)", "vendor": "字节跳动", "style": "openai",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "doubao-1-5-pro-32k-250115",
        "env_keys": ["DOUBAO_API_KEY", "ARK_API_KEY"],
    },
    "claude": {
        "label": "Claude", "vendor": "Anthropic", "style": "anthropic",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-5",
        "env_keys": ["ANTHROPIC_API_KEY"],
    },
    "gemini": {
        "label": "Gemini", "vendor": "Google", "style": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    },
}

# 决策脑/生成类任务的默认回退顺序（2026-07-20 实测：tongyi/kimi/glm 可用，
# deepseek/doubao 余额不足、hunyuan 模型迁移、spark 授权异常、claude/gemini 密钥无效——
# 密钥/余额恢复后自动生效；可用 MX_BRAIN_PROVIDERS 覆盖顺序）
DEFAULT_CHAIN = ["tongyi", "kimi", "glm", "deepseek", "hunyuan", "doubao", "spark", "claude", "gemini"]


def get_key(provider):
    cfg = PROVIDERS.get(provider) or {}
    for k in cfg.get("env_keys", []):
        v = os.environ.get(k)
        if v:
            return v
    return None


def has_key(provider):
    return bool(get_key(provider))


def model_of(provider):
    cfg = PROVIDERS[provider]
    return os.environ.get(f"MX_{provider.upper()}_MODEL", cfg["model"])


def available():
    """返回当前有密钥、可实测的 provider id 列表（顺序稳定）。"""
    return [p for p in PROVIDERS if has_key(p)]


def _post_json(url, headers, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        return None, f"http_{e.code}: {detail}"
    except Exception as e:  # noqa: BLE001
        return None, f"request_failed: {e}"


def chat(provider, user, system=None, model=None, max_tokens=1500,
         temperature=0.4, timeout=150):
    """单厂商一次对话。返回 (text, err)；err 为 None 表示成功。"""
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return None, f"unknown_provider: {provider}"
    key = get_key(provider)
    if not key:
        return None, f"no_key: {'/'.join(cfg['env_keys'])}"
    mdl = model or model_of(provider)

    if cfg["style"] == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
                   "Content-Type": "application/json; charset=utf-8"}
        payload = {"model": mdl, "max_tokens": max_tokens, "temperature": temperature,
                   "messages": [{"role": "user", "content": user}]}
        if system:
            payload["system"] = system
        body, err = _post_json(cfg["url"], headers, payload, timeout)
        if err:
            return None, f"{provider}: {err}"
        try:
            parts = body.get("content") or []
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            return (text or None), (None if text else f"{provider}: empty_content")
        except Exception:  # noqa: BLE001
            return None, f"{provider}: bad_response_shape"

    # OpenAI 兼容
    headers = {"Authorization": f"Bearer {key}",
               "Content-Type": "application/json; charset=utf-8"}
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}]
    payload = {"model": mdl, "messages": messages,
               "max_tokens": max_tokens, "temperature": temperature}
    body, err = _post_json(cfg["url"], headers, payload, timeout)
    if err:
        return None, f"{provider}: {err}"
    try:
        text = body["choices"][0]["message"]["content"]
        return (text or None), (None if text else f"{provider}: empty_content")
    except Exception:  # noqa: BLE001
        return None, f"{provider}: bad_response_shape"


def chat_fallback(user, system=None, chain=None, **kw):
    """按回退链依次尝试，返回 (text, provider_id, errors)。全失败时 text=None。"""
    order = chain or [p.strip() for p in
                      os.environ.get("MX_BRAIN_PROVIDERS", ",".join(DEFAULT_CHAIN)).split(",")
                      if p.strip()]
    errors = []
    for p in order:
        if not has_key(p):
            continue
        text, err = chat(p, user, system=system, **kw)
        if text:
            return text, p, errors
        errors.append(str(err)[:200])
    return None, None, errors


if __name__ == "__main__":
    print("available providers:", available())
