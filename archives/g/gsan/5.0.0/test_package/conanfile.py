#!/usr/bin/env python3
"""Test package for gsan 5.0.0."""
import sys
from conan import ConanFile


class GsanTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # gsan is a pure-Python application; its logic test runs on the build
        # host (the CI runner), not on the OHOS target device. We run it
        # unconditionally — guarding with can_run() would skip the test during
        # OHOS cross-compilation (host != OHOS/aarch64) and trip the CI's
        # destructive negative test (L1e), which would flag it as a fake test.
        self.run(f'"{sys.executable}" test_gsan.py', env="conanrun")
