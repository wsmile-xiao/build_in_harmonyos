#!/usr/bin/env python3
"""Consumer test for the packaged phyx command suite."""

import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PhyxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["phyx"]
        # Keep the cross-build branch dependent on the real package as well:
        # CI's destructive R34 check removes bin/ and expects this test to fail.
        probe = os.path.join(dep.package_folder, "bin", "pxlssq")
        if not os.path.isfile(probe):
            raise ConanException(f"required packaged executable missing: {probe}")
        wrong_cpu = (str(self.settings.arch) == "armv8" and
                     platform.machine().lower() not in ("aarch64", "arm64"))
        if not can_run(self) or wrong_cpu:
            self.output.warning(
                "Cross build cannot execute OHOS binaries; native package tests run in CI")
            return
        test_data = os.path.join(dep.package_folder, "share", "phyx", "TEST")
        script = os.path.join(self.source_folder, "test_phyx.py")
        self.run(f'python3 "{script}" "{test_data}"', env="conanrun")
