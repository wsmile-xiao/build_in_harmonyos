#!/usr/bin/env python3
"""Conan test_package for mkcue 1 (L1 consumer test).

mkcue is a CLI tool without --version/--help: the only observable surface
without CD hardware is the argument/device error path plus the OHOS ELF
properties.  test_mkcue.py really executes the packaged binary along 9
deterministic assertions (6 upstream-behaviour + 3 ohos-platform) and prints
a "RESULT: P passed, F failed" trailer line.  This recipe parses that line
for the real counts (never string-counting stdout) and emits the HMBS
machine-evidence markers the rule4 gate requires.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  RESULT trailer (real counts, not estimates).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). Re-emitted here so evidence survives Conan
  cache hits (build() runs no upstream tests).
"""

import json
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MkcueTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("mkcue consumer test skipped: target cannot run")
            return

        dep = self.dependencies["mkcue"]
        package = dep.package_folder
        bin_dir = os.path.join(package, "bin")
        script = os.path.join(self.recipe_folder, "test_mkcue.py")
        log = os.path.join(self.build_folder, "mkcue-cases.log")
        self.run(
            f'"{sys.executable}" "{script}" "{bin_dir}" --log "{log}"',
            env="conanrun",
        )

        out = ""
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_mkcue.py log:\n" + "\n".join(out.splitlines()[-25:]))

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        # Only one data source: no fallbacks, no arithmetic patch-ups.
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_mkcue.py produced no RESULT line - harness broken "
                f"(log: {log})"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        # Self-check identities before emitting: counts must be consistent.
        # executed == discovered here (no SKIP produced by the script except
        # fatal paths, which raise above); executed + skipped <= discovered.
        if discovered <= 0:
            raise ConanException(
                f"test_mkcue.py reported no cases (discovered={discovered})"
            )
        ok = failed == 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "python3 test_mkcue.py <package>/bin",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_mkcue.py failed: %d/%d cases failed" % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts.
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "make -n check (upstream defines no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "mkcue 1 上游无可接入的测试套件：tarball 无 tests/ 目录，"
                "GNUmakefile.in 仅有 all/mkcue/clean/maintainer-clean/install/dist 目标，"
                "无 check/test 目标；Debian 打包亦无测试目标"
                "（详见 test_package/MANIFEST.yml 审计）；本 test_package 对打包二进制做 9 条消费端校验"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("mkcue consumer test_package passed")
