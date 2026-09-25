#!/usr/bin/env python3
"""Conan test_package conanfile — pngmeta 1.11."""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class PngmetaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        dep = self.dependencies["pngmeta"]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        pngmeta = os.path.join(bindir, "pngmeta")
        # L1e negative test: the assertion fails if bin/ is sabotaged, which
        # proves this test really depends on the package under test.
        assert os.path.isfile(pngmeta), f"pngmeta not found at {pngmeta}"

        test_script = os.path.join(os.path.dirname(__file__), "test.py")
        self.run(f"python3 {test_script} {bindir}", env="conanrun")
