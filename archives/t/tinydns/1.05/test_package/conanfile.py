#!/usr/bin/env python3
"""Conan test_package -- tinydns 1.05 (R34/PF3: 实质执行被测二进制)."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TinydnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # simple layout for test_package
        self.folders.build = "."
        self.folders.generators = "."

    def build(self):
        # No compilation needed for shell script test
        pass

    def test(self):
        if not can_run(self):
            raise Exception(
                "can_run() is False: refusing to report a green test without "
                "executing the packaged binaries."
            )

        test_script = os.path.join(self.source_folder, "test_tinydns.sh")
        if not os.path.isfile(test_script):
            raise Exception(f"Test script not found: {test_script}")

        os.chmod(test_script, 0o755)

        # Any failure here (including "Operation not permitted" / exit 126) is
        # propagated as a test failure on purpose: an execution problem must be
        # visible in CI rather than being downgraded to a passing skip.
        self.run(f"bash {test_script}", env="conanrun")