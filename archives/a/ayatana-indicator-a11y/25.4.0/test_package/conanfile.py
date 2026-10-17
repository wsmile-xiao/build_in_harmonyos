#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-a11y 25.4.0 L1 test.

The product is a daemon binary (no public library API), so the L1 test runs
a functional smoke test (R34): 1) verify the ELF daemon under libexec/ is
executable, 2) launch it — a clean exit (no D-Bus session bus in the CI
sandbox) or a still-running process (session bus present) are both passes,
any other exit code is a failure, 3) verify the installed data artifacts
(GSettings schema, Ayatana indicator descriptor, D-Bus interface XML, icon
and autostart desktop file).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AyatanaIndicatorA11yTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # The daemon installs under libexec/ (not bin/), so pass the package
        # folder explicitly instead of relying on PATH lookup.
        pkg = self.dependencies[self.tested_reference_str].package_folder
        os.environ["A11Y_PKG"] = pkg
        self.run(f"{bash} test.sh", env="conanrun")
