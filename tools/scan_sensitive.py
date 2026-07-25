# -*- coding: utf-8 -*-
"""敏感信息扫描器（密钥 + 越界 PII），规则单一来源、多处复用。

三种模式，按"发布时机"由早到晚排列：
  --worktree <dir>          扫描工作区文件（本地 pre-commit、CI 开跑前的体检）
  --staged <repo>           扫描暂存区，即本次提交将发布出去的**确切**内容。
                            仓库已公开，这是 CI 提交闸门唯一严丝合缝的口径
  --git-all-objects <repo>  扫描每一个 blob（含已删除文件的历史版本、不可达对象），
                            用于公开前的历史复扫

设计纪律：
  - 本文件自身会进入公开仓库，因此**规则里不得写死任何真实 PII**。
    需要匹配具体账号时用通用正则（如任意 gmail 地址），或运行时经
    --extra-pattern 传入，绝不硬编码。
  - 官网已主动公开的联系方式属允许清单（见 ALLOW_SUBSTRINGS），不算泄露：
    铭信官网 Footer 与中英文联系页、JSON-LD 均已对外发布。
  - 命中即以退出码 1 结束，供 CI 直接卡住流水线。

复现：
  python tools/scan_sensitive.py --worktree .
  python tools/scan_sensitive.py --staged .
  python tools/scan_sensitive.py --git-all-objects <path-to-repo.git> --extra-pattern "xxx"
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

# —— 供应商密钥前缀与私钥（高置信度，命中即阻断） ——
SECRET_RULES: list[tuple[str, str]] = [
    ("openai_key", r"\bsk-[A-Za-z0-9]{20,}"),
    ("anthropic_key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_\-]{35}"),
    ("github_pat_classic", r"\bghp_[A-Za-z0-9]{36}"),
    ("github_pat_fine", r"\bgithub_pat_[A-Za-z0-9_]{50,}"),
    ("github_oauth", r"\bgho_[A-Za-z0-9]{36}"),
    ("gitlab_pat", r"\bglpat-[A-Za-z0-9_\-]{20}"),
    ("slack_bot", r"\bxoxb-[A-Za-z0-9\-]{20,}"),
    ("pem_private_key", r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("gcp_service_account", r'"type"\s*:\s*"service_account"'),
    ("gcp_private_key_field", r'"private_key"\s*:\s*"-----BEGIN'),
    ("oauth_refresh_token", r'"refresh_token"\s*:\s*"[A-Za-z0-9_\-./]{20,}"'),
    # 把凭据拼进 URL 的写法（如 https://user:token@host）。
    # 排除含 $ 的情形：那是 CI/shell 变量插值（如 ${GH_PAT}），并非真实凭据。
    ("url_embedded_credential", r"https://[^/\s:@$]+:[^/\s@$]{8,}@[A-Za-z0-9.\-]+"),
]

# —— 越界 PII：不写死具体账号，用通用正则 ——
PII_RULES: list[tuple[str, str]] = [
    # 个人邮箱域（企业公开邮箱走 ALLOW_SUBSTRINGS 放行）
    ("personal_mailbox", r"[A-Za-z0-9._%+\-]+@(?:gmail\.com|qq\.com|163\.com|139\.com|126\.com|outlook\.com|hotmail\.com)"),
]

# —— 结构性敏感产物：整站资产清单一旦公开即等于披露域名矩阵 ——
PATH_RULES: list[tuple[str, str]] = [
    ("gsc_property_inventory", r"gsc_properties\.json$"),
    ("gsc_live_inspection", r"gsc_[a-z0-9_]*inspection\.json$"),
    ("external_actions_status", r"external_actions_status\.json$"),
    ("browser_session_state", r"(?:storage_state|browser_state)[^/]*\.json$"),
    ("credential_file", r"\.(?:pem|p12|pfx|jks|ppk)$|(?:^|/)id_rsa|credentials.*\.json$|service.*account.*\.json$|client_secret.*\.json$"),
]

# 官网已对外公开的联系方式 —— 属公司主动披露，非泄露，予以放行。
# 依据：amd 仓库 site/src/components/Footer.tsx、(zh)/contact、(en)/en/contact、
#       lib/seo/structured.ts 的 JSON-LD 均已发布这些值。
ALLOW_SUBSTRINGS: tuple[str, ...] = (
    "mingxin@agentmail.to",
    "13426086861@139.com",
    "users.noreply.github.com",
    "geo-autopilot@users.noreply.github.com",
    "example.com",
    "your-account@gmail.com",
    "<your-google-account>",
)

# 扫描时跳过的路径（二进制与体积产物，降噪不降覆盖）。
# official_website / offsite_github 是独立仓库的本地 clone（Windows 下前者为目录联接），
# 已被 .gitignore 排除、不进入本仓库版本库，各自有独立的扫描责任，故跳过。
SKIP_DIR_PARTS = (".git", "__pycache__", "node_modules", ".venv", "site-packages",
                  ".next", ".vercel", "official_website", "offsite_github", "_sites")
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".woff",
            ".woff2", ".ttf", ".zip", ".gz", ".whl", ".so", ".dll", ".pyc")


def _compile(rules):
    return [(name, re.compile(pat)) for name, pat in rules]


def _allowed(line: str) -> bool:
    return any(a in line for a in ALLOW_SUBSTRINGS)


def _redact(s: str) -> str:
    """只暴露前 6 字符与长度，避免扫描报告本身变成泄露源。"""
    s = s.strip()
    return f"{s[:6]}…(len={len(s)})" if len(s) > 8 else "…"


def scan_text(text: str, where: str, content_rules, path_rules_hit=None) -> list[str]:
    findings = list(path_rules_hit or [])
    for i, line in enumerate(text.splitlines(), 1):
        if _allowed(line):
            continue
        for name, rx in content_rules:
            m = rx.search(line)
            if m:
                findings.append(f"[{name}] {where}:{i} -> {_redact(m.group(0))}")
    return findings


def _gitignored(root: str, rels: list[str]) -> set[str]:
    """批量问 git 哪些路径被忽略。被忽略的文件不会进入版本库，不构成公开泄露。

    必须走 -z（NUL 分隔）的字节流：Windows 上文本模式会把 \\n 换成 \\r\\n，
    git 会收到带 \\r 的路径而全部匹配失败（曾因此静默漏过 .env）。
    """
    if not rels:
        return set()
    payload = b"\x00".join(r.encode("utf-8") for r in rels) + b"\x00"
    try:
        p = subprocess.run(["git", "-C", root, "check-ignore", "-z", "--stdin"],
                           input=payload, capture_output=True)
    except OSError:
        return set()
    return {x.decode("utf-8", "ignore").replace("\\", "/")
            for x in p.stdout.split(b"\x00") if x}


def scan_worktree(root: str, content_rules, path_rules, extra,
                  respect_gitignore: bool = True) -> list[str]:
    candidates: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
            candidates.append(rel)

    ignored = _gitignored(root, candidates) if respect_gitignore else set()
    if ignored:
        print(f"[scan] 跳过 .gitignore 已排除的 {len(ignored)} 个文件（不入库，非泄露面）")

    findings: list[str] = []
    for rel in candidates:
        if rel in ignored:
            continue
        full = os.path.join(root, rel)
        hits = [f"[{n}] {rel} -> 敏感文件路径"
                for n, rx in path_rules if rx.search(rel)]
        if os.path.splitext(rel)[1].lower() in SKIP_EXT:
            findings.extend(hits)
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        findings.extend(scan_text(text, rel, content_rules + extra, hits))
    return findings


def scan_staged(root: str, content_rules, path_rules, extra) -> list[str]:
    """扫描已 `git add` 的内容——即本次提交将要发布出去的**确切**字节。

    公开仓库里这是唯一严丝合缝的口径：`--worktree` 会连引擎生成但不提交的中间
    产物一起扫（误杀合法运行），`--git-all-objects` 只看已入库的历史（太晚了）。
    读 index 而非工作区文件，因为两者可能不一致（add 之后又被改写）。
    """
    listing = subprocess.run(
        ["git", "-C", root, "diff", "--cached", "--name-only", "-z",
         "--diff-filter=ACMR"],
        capture_output=True).stdout
    rels = [x.decode("utf-8", "ignore") for x in listing.split(b"\x00") if x]
    if not rels:
        print("[scan] 暂存区为空，本次无内容将被发布")
        return []

    findings: list[str] = []
    scanned = skipped = 0
    for rel in rels:
        hits = [f"[{n}] {rel} -> 敏感文件路径"
                for n, rx in path_rules if rx.search(rel)]
        if os.path.splitext(rel)[1].lower() in SKIP_EXT:
            findings.extend(hits)
            skipped += 1
            continue
        blob = subprocess.run(["git", "-C", root, "show", f":{rel}"],
                              capture_output=True).stdout
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            findings.extend(hits)
            skipped += 1
            continue
        scanned += 1
        findings.extend(scan_text(text, rel, content_rules + extra, hits))
    print(f"[scan] 暂存区待发布文件 {len(rels)} 个：已扫描 {scanned} 个，"
          f"跳过二进制/免扫后缀 {skipped} 个")
    return findings


def scan_git_all_objects(repo: str, content_rules, path_rules, extra) -> list[str]:
    """扫描每一个 blob（含不可达对象）+ 全历史出现过的路径。"""
    findings: list[str] = []

    paths = subprocess.run(
        ["git", "-C", repo, "log", "--all", "--pretty=format:", "--name-only",
         "--diff-filter=A"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
    for p in {x.strip() for x in paths.splitlines() if x.strip()}:
        for n, rx in path_rules:
            if rx.search(p):
                findings.append(f"[{n}] (history path) {p} -> 敏感文件曾进入版本库")

    listing = subprocess.run(
        ["git", "-C", repo, "cat-file", "--batch-all-objects",
         "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
    blobs = [ln.split()[0] for ln in listing.splitlines()
             if len(ln.split()) == 3 and ln.split()[1] == "blob"
             and int(ln.split()[2]) < 4_000_000]

    # 单个 cat-file --batch 进程流式取全部 blob：逐个 spawn 在数千对象时慢一个数量级。
    scanned = skipped = 0
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for sha in blobs:
            proc.stdin.write(sha.encode() + b"\n")
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3:
                break
            size = int(header[2])
            raw = proc.stdout.read(size)
            proc.stdout.read(1)  # 结尾换行
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                skipped += 1
                continue
            scanned += 1
            findings.extend(scan_text(text, f"blob {sha[:10]}", content_rules + extra))
    finally:
        proc.stdin.close()
        proc.wait()
    print(f"[scan] 已扫描 blob {scanned} 个，跳过二进制 {skipped} 个，总计 {len(blobs)} 个")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree")
    ap.add_argument("--staged", help="扫描该仓库暂存区（本次提交将发布的确切内容）")
    ap.add_argument("--git-all-objects")
    ap.add_argument("--extra-pattern", action="append", default=[],
                    help="运行时追加的正则（用于不宜入库的具体 PII）")
    ap.add_argument("--secrets-only", action="store_true",
                    help="只查密钥，不查 PII（用于噪声敏感场景）")
    ap.add_argument("--no-gitignore", action="store_true",
                    help="连 .gitignore 已排除的文件一起查（默认跳过，因其不入库）")
    args = ap.parse_args()

    rules = list(SECRET_RULES) if args.secrets_only else list(SECRET_RULES) + list(PII_RULES)
    content_rules = _compile(rules)
    path_rules = _compile(PATH_RULES)
    extra = _compile([(f"extra_{i}", p) for i, p in enumerate(args.extra_pattern)])

    if args.git_all_objects:
        findings = scan_git_all_objects(args.git_all_objects, content_rules, path_rules, extra)
        target = args.git_all_objects
    elif args.staged:
        findings = scan_staged(args.staged, content_rules, path_rules, extra)
        target = f"{args.staged} (staged)"
    elif args.worktree:
        findings = scan_worktree(args.worktree, content_rules, path_rules, extra,
                                 respect_gitignore=not args.no_gitignore)
        target = args.worktree
    else:
        ap.error("需指定 --worktree、--staged 或 --git-all-objects")
        return 2

    if findings:
        print(f"\n[FAIL] {target}: 命中 {len(findings)} 条敏感项")
        for f in sorted(set(findings)):
            print("  " + f)
        return 1
    print(f"\n[OK] {target}: 0 命中")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
