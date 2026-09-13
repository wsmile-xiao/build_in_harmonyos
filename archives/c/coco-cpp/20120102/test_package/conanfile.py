#!/usr/bin/env python3
"""Conan test_package for coco-cpp 20120102 — runs the packaged cococpp on a
real grammar through the consumer driver test_cococpp.py and asserts
scanner/parser generation (R34)."""
import os
import tempfile

from conan import ConanFile


class CocoCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["coco-cpp"]
        pkg_folder = dep.package_folder
        work = tempfile.mkdtemp(prefix="cococpp-test-")
        script = os.path.join(self.recipe_folder, "test_cococpp.py")
        self.run(f'python3 "{script}" "{pkg_folder}" "{work}"', env="conanrun")
