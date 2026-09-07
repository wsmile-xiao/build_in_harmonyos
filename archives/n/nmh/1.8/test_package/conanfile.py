#!/usr/bin/env python3
"""nmh 1.8 consumer smoke tests (run under the conanrun environment)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class NmhTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    EXPECT_TOTAL = 58

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["nmh"].package_folder
        work = os.path.join(self.build_folder, "work")
        runner = os.path.join(self.build_folder, "nmh_test_runner.sh")
        shutil.copy2(
            os.path.join(self.recipe_folder, "src", "nmh_test_runner.sh"),
            runner,
        )
        log = os.path.join(self.build_folder, "nmh-tests.log")
        self.run(
            f'bash "{runner}" "{package}" "{work}" > "{log}" 2>&1',
            env="conanrun",
            ignore_errors=True,
        )
        lines = open(log, encoding="utf-8", errors="replace").read()
        self.output.info(lines)

        summary = {}
        for line in lines.splitlines():
            if line.startswith("NMH_TEST_SUMMARY "):
                for token in line.split()[1:]:
                    key, _, value = token.partition("=")
                    summary[key] = int(value)

        total = summary.get("total")
        passed = summary.get("pass")
        failed = summary.get("fail")
        if (total, passed, failed) != (self.EXPECT_TOTAL, self.EXPECT_TOTAL, 0):
            tail = [ln for ln in lines.splitlines() if ln.startswith("FAIL ")][-20:]
            raise ConanException(
                f"nmh test expectations not met: "
                f"expected total={self.EXPECT_TOTAL} pass={self.EXPECT_TOTAL} "
                f"fail=0, got total={total} pass={passed} fail={failed}; "
                f"failing cases: {' | '.join(tail)}"
            )
        self.output.info(f"NMH_TEST_PACKAGE_PASS={passed}/{total}")
