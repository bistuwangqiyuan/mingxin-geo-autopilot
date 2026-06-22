# -*- coding: utf-8 -*-
"""用 bl(DashScope qwen-image-2.0) 生成苹果视觉风格的封面/扉页配图。

幂等：目标文件已存在则跳过（避免重复消耗）；--force 强制重生。
复现：python gen_heroes.py [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

_STYLE = ("Apple Keynote style premium hero image, ultra-clean minimalist, soft "
          "light-gray to white gradient background, subtle System Blue (#0A84FF) and "
          "indigo accents, elegant depth of field, generous white space, high-end "
          "enterprise tech aesthetic, 16:9, no text, no words, no logos. Subject: ")

HEROES = {
    "cover_hero.png": "many glowing neural network nodes converging and pointing to one trusted bright sphere at the center, representing multiple AI models citing one brand",
    "divider_exec.png": "a single bright focal sphere with soft radiating light rays on a clean surface, sense of clarity and focus",
    "divider_baseline.png": "minimalist floating translucent analytics panels with soft bar and line charts and a radar, data measurement dashboard, very clean",
    "divider_category.png": "precise concentric translucent target rings with one glowing node hitting the exact center, niche focus",
    "divider_method.png": "an elegant translucent blueprint wireframe of a data pipeline with connected glowing stages, technical and precise",
    "divider_levers.png": "four elegant translucent vertical pillars or levers of soft blue light standing in a row on a clean surface",
    "divider_roadmap.png": "an ascending series of glowing translucent stepped platforms rising toward the upper right, a path of progress",
    "divider_risk.png": "a balanced translucent scale and a soft glowing shield, calm sense of trust and prudence",
    "divider_review.png": "a smooth circular loop of glowing arrows representing a continuous improvement cycle, on a clean surface",
    "divider_appendix.png": "a neat fanned stack of translucent glowing document cards, an organized index, minimalist",
}


def _bl():
    for c in ("bl.cmd", "bl.exe", "bl"):
        p = shutil.which(c)
        if p:
            return p
    g = os.path.expanduser(r"~\AppData\Roaming\npm\bl.cmd")
    return g if os.path.exists(g) else None


def gen_one(bl, name, subject, force=False):
    target = os.path.join(FIG, name)
    if os.path.exists(target) and not force:
        print(f"  skip (exists): {name}")
        return True
    prompt = _STYLE + subject
    proc = subprocess.run(
        [bl, "image", "generate", "--prompt", prompt, "--size", "1664*928",
         "--out-dir", FIG, "--output", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    out = proc.stdout or ""
    start = out.find("{")
    if start < 0:
        print(f"  FAIL {name}: {out[:160]}")
        return False
    try:
        data = json.loads(out[start:out.rfind('}') + 1])
        saved = data.get("saved", [])
    except Exception as e:
        print(f"  FAIL {name}: parse {e}")
        return False
    if not saved:
        print(f"  FAIL {name}: no saved file")
        return False
    src = saved[0]
    if not os.path.isabs(src):
        src = os.path.join(BASE, src)
    shutil.move(src, target)
    print(f"  OK {name}  ({os.path.getsize(target)/1e6:.2f} MB)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    bl = _bl()
    if not bl:
        print("ERROR: bl not found")
        return
    ok = 0
    for name, subject in HEROES.items():
        if gen_one(bl, name, subject, force=args.force):
            ok += 1
    print(f"Done. {ok}/{len(HEROES)} heroes ready in {FIG}")


if __name__ == "__main__":
    main()
