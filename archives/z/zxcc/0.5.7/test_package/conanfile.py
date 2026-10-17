#!/usr/bin/env python3
"""Conan test_package — real-execution smoke test for zxcc.

Runs test_zxcc.py, which executes the packaged tools (zxcc/zxas) and
verifies BIOS startup paths and bindirs wiring (R34: real execution).
"""
import os

from conan import ConanFile


class ZxccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # execute the packaged tools via the real test script (R34)
        script = os.path.join(self.source_folder, "test_zxcc.py")
        bindir = self.dependencies["zxcc"].cpp_info.bindirs[0]
        python = os.environ.get("PYTHON", "python3")
        self.run(
            f"ZXCC_TEST_BINDIR={bindir} {python} {script}",
            env="conanrun",
        )
