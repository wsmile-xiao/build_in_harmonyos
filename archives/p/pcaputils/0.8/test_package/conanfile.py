#!/usr/bin/env python3
"""Conan test_package — pcaputils 0.8 L1 smoke test.

Runs each shipped CLI tool with no arguments. Each tool's argument parser
detects the missing capture source, prints its "Usage:" banner and exits
non-zero. This proves the binaries were built for OHOS, dynamically link
libpcap/Judy successfully, and reach their own code path (not a loader crash).
"""
import os

from conan import ConanFile


class PcaputilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {script}", env="conanrun")
