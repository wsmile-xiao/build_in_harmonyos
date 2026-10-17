#!/usr/bin/env python3
"""Consumer test for aesfix 1.0.1."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class AesfixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: packaged CLI smoke requires a runnable target")
            return

        package_folder = self.dependencies["aesfix"].package_folder
        aesfix = os.path.join(package_folder, "bin", "aesfix")
        sample = os.path.join(package_folder, "share", "aesfix", "samples", "sched.100")
        script = os.path.join(self.source_folder, "test.sh")

        if not os.path.isfile(aesfix):
            raise AssertionError(f"packaged aesfix binary not found: {aesfix}")
        if not os.path.isfile(sample):
            raise AssertionError(f"packaged aesfix sample not found: {sample}")

        self.run(
            " ".join(shlex.quote(part) for part in ["sh", script, aesfix, sample]),
            env="conanrun",
        )
