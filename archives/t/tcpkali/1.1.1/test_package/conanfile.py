#!/usr/bin/env python3
"""Conan test_package — tcpkali 1.1.1

Smoke test: runs tcpkali --version to verify the binary is functional.
This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class TcpkaliTestConan(ConanFile):
    """test_package for tcpkali executable — runs tcpkali --version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Must actually invoke the tcpkali binary (not a stub)
        tcpkali_bin = os.path.join(
            self.dependencies["tcpkali"].cpp_info.bindirs[0], "tcpkali"
        )
        self.run(f'"{tcpkali_bin}" --version', env="conanrun")
