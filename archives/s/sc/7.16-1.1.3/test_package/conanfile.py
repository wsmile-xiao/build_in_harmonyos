#!/usr/bin/env python3
"""test_package for sc 7.16-1.1.3 — consumer CLI functional checks."""

import json
import os
import shutil

from conan import ConanFile


class ScTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _select_shell(self):
        # profile [buildenv] 硬编码 CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash，
        # 在缺该路径的预检机上不可执行（m4 同因失败）。只接受真实存在且可
        # 执行的 shell，否则回退到 /bin/sh（test.sh 仅用 POSIX 语法）。
        for cand in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/bin/sh",
            "/system/bin/sh",
            "sh",
        ):
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            elif shutil.which(cand):
                return cand
        return "sh"

    def test(self):
        bash = self._select_shell()
        pkg = self.dependencies["sc"].package_folder
        work = os.path.join(self.build_folder, "sc-consumer-work")
        os.makedirs(work, exist_ok=True)
        self.run(
            'HOME="{0}/home" {1} test.sh "{2}" "{0}"'.format(work, bash, pkg),
            env="conanrun",
        )
        try:
            upstream = {
                "status": "no_tests",
                "framework": "custom",
                "command": "no upstream test target",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "sc 7.16_1.1.3 audited: no tests/ or test/ directory, no TESTS/check target in Makefile.in, no ctest/gtest/pytest registration; only tutorial.sc sample file",
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                upstream, ensure_ascii=False
            )
            print(msg, flush=True)
            self.output.info(msg)
        except Exception:
            pass
