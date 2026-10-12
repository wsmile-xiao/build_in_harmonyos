#!/usr/bin/env python3
"""Conan test_package for mtu 1.5.1 (L1 consumer test).

mtu is an application; the test validates that the packaged `mtu` binary
actually executes on the target through its argument-parsing usage path
(no raw socket or network needed: bare `mtu` and `mtu -z` both reach
usage() which prints to stderr and exits 3).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). Re-emitted here so evidence survives Conan
  cache hits (build() may be skipped on preflight).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class MtuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "mtu")
        if not os.path.isfile(binary):
            self.output.error("mtu binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        test_script = os.path.join(self.recipe_folder, "test_mtu.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s > %s 2>&1" % (
            shlex.quote("sh"),
            shlex.quote(test_script),
            shlex.quote(binary),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_mtu.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_mtu.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_mtu.sh <pkg>/bin/mtu",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_mtu.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "pingu-1.5.1 上游无可接入的测试套件：31KB 源码包内无 tests/ 或 test/ 目录，src/Makefile 与顶层 Makefile 仅有 all/install/clean 目标而无 check/test 目标，configure 亦无测试选项（详见 test_package/MANIFEST.yml 审计）；本 test_package 对打包二进制做 4 条消费端冒烟校验",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("mtu functional test_package passed")
