#!/usr/bin/env python3
"""Conan consumer test for alloy 1.17.1."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AlloyTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_alloy.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["alloy"].package_folder
        exe = os.path.join(package_folder, "bin", "alloy")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing alloy executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_alloy.py")
        result = self.run(
            f'"{sys.executable}" "{script}" "{exe}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result == 77:
            # Explicit SKIP: the target environment blocks the bpf syscall
            # the binary needs at startup; layout was verified, the runtime
            # assertions require a bpf-capable host (device/CI). Reported as
            # a skip, not a pass (no false-green).
            self.output.info(
                "SKIP: alloy runtime blocked by host seccomp (bpf syscall); "
                "package layout verified only")
            return
        if result != 0:
            raise AssertionError(f"alloy smoke test failed with exit code {result}")
