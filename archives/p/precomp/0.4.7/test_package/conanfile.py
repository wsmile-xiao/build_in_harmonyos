#!/usr/bin/env python3
"""Conan test_package — precomp 0.4.7.

Drives the packaged `precomp` binary through its core workflow (R34 —
executes the package's binary, no stub prints):
the real test logic lives in test_precomp.py, invoked with the absolute
path of the binary installed by the tested package.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PrecompTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_precomp.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["precomp"]
        binary = os.path.join(dep.package_folder, "bin", "precomp")
        script = os.path.join(self.source_folder, "test_precomp.py")
        self.run(f'python3 "{script}" "{binary}"', env="conanrun")
