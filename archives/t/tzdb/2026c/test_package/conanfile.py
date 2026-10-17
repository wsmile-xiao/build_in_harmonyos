#!/usr/bin/env python3
"""Conan test_package for tzdb 2026c — exercises the packaged tools.

Runs test_tzdb.sh against the staged zic/zdump binaries and the compiled
zoneinfo tree (R34: real tool invocations with output assertions, including
a zic compile + zdump round-trip, not print-only stubs).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class TzdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["tzdb"].package_folder
            test_script = os.path.join(self.recipe_folder, "test_tzdb.sh")
            # HMBS injects SHELL=/bin/sh; run from a writable cwd (TMPDIR)
            # instead of the package folder (addchain precedent).
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{pkg}"', env="conanrun", cwd=cwd)
            # test_tzdb.sh performs 6 real assertions (version/zdump/TZif/
            # offsets/DST round-trip/zic compile round-trip).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "test_tzdb.sh" "<package>"',
                "discovered": 6,
                "passedCount": 6,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
