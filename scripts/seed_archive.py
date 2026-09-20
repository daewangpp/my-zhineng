# -*- coding: utf-8 -*-
"""真实模式跑 3 个用例填充档案库(用于正式截图)。"""
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from codetutor.orchestrator import Orchestrator  # noqa: E402
from tests.test_cases import CASES  # noqa: E402

orch = Orchestrator()
print("mock 模式:", orch.mock_mode)
for i in [0, 1, 5]:
    r = orch.analyze(CASES[i]["code"], CASES[i]["symptom"])
    print("%s -> %s | 验证:%s | 归档:#%s" % (
        CASES[i]["name"], r["diagnosis"]["error_type"],
        r["fix"].get("verified"), r.get("archive_id")))
