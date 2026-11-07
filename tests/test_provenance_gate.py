# -*- coding: utf-8 -*-
"""来源闸门单元测试：无依据的参数必须被拒绝，事实源里有的数字必须放行。

运行：python -m unittest tests/test_provenance_gate.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "geo_autopilot"))

from provenance_gate import build_corpus, provenance_issues  # noqa: E402

SITE = os.environ.get("MX_SITE_URL", "https://lvsuan.top")
CORPUS = build_corpus(os.path.join(ROOT, "business_plan", "outputs", "results.json"), SITE)


class ProvenanceGateTests(unittest.TestCase):
    def test_rejects_unsourced_latency(self):
        self.assertTrue(provenance_issues("sub-12μs commit latency", CORPUS, SITE))

    def test_rejects_unsourced_standard(self):
        self.assertTrue(provenance_issues("EU AI Act Article 16 compliant", CORPUS, SITE))

    def test_rejects_unsourced_uplift(self):
        self.assertTrue(provenance_issues("吞吐提升 +34%（R3）", CORPUS, SITE))

    def test_rejects_unsourced_acronyms(self):
        self.assertTrue(provenance_issues("TPM 2.0 + RCIB 绑定", CORPUS, SITE))

    def test_rejects_legacy_domain(self):
        self.assertTrue(provenance_issues("详见 https://mingxinstorage.xyz/fx100", CORPUS, SITE))

    def test_rejects_unsourced_path_on_current_domain(self):
        self.assertTrue(provenance_issues("接口：" + SITE + "/metrics", CORPUS, SITE))

    def test_rejects_bare_legacy_domain_with_path(self):
        self.assertTrue(provenance_issues("见 mingxinstorage.xyz/metrics 接口", CORPUS, SITE))

    def test_rejects_invented_path_without_scheme(self):
        self.assertTrue(provenance_issues("文档：lvsuan.top/docs/fx100-ray-serve", CORPUS, SITE))

    def test_accepts_sourced_numbers(self):
        text = "推理吞吐提升 29–40%（R2/R3），首 token 延迟降低 26–32%（R2）。"
        self.assertEqual(provenance_issues(text, CORPUS, SITE), [])

    def test_accepts_current_domain_root(self):
        self.assertEqual(provenance_issues("详见 " + SITE, CORPUS, SITE), [])


if __name__ == "__main__":
    unittest.main()
