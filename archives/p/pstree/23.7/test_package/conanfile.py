#!/usr/bin/env python3
"""Conan test_package — pstree 23.7 CLI tool verification.

pstree is a CLI tool, not a library. The test uses VirtualRunEnv to locate
the installed binary and runs it against the real /proc filesystem (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PstreeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bin_dir = self.dependencies["pstree"].cpp_info.bindirs[0]
        pstree_bin = os.path.join(bin_dir, "pstree")
        test_script = os.path.join(self.source_folder, "test_pstree.sh")
        self.run(f'sh "{test_script}" "{pstree_bin}"', env="conanrun")
