#!/usr/bin/env python3
"""test_package for spinner 1.2.4 — executes the packaged `spinner` binary.

Consumer verification: invoke the installed binary the way a real user would
(license display, illegal-option usage path, TERM compatibility guard, and a
real daemonised run on a pty) and judge the observable output plus exit codes.

The OHOS runner's /system/bin/sh is mksh and cannot exec ELF binaries, so the
test script is launched through bash (same workaround as the 2048.c precedent).
"""
import os

from conan import ConanFile


class SpinnerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS runner's /system/bin/sh is mksh and cannot exec ELF binaries, so the
        # POSIX test script is launched through bash (same workaround as the 2048.c
        # precedent). The packaged binary path is passed in as $1 rather than being
        # resolved through conanrun PATH, so the assertion is pinned to this exact
        # package folder instead of whatever happens to be first on PATH.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        spinner_bin = os.path.join(
            self.dependencies["spinner"].package_folder, "bin", "spinner"
        )
        self.run(f"{bash} test.sh {spinner_bin}", env="conanrun")
