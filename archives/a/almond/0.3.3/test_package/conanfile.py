#!/usr/bin/env python3
"""Consumer test for almond/0.3.3."""

import os
import sys

from conan import ConanFile


class AlmondTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.test_requires("quickjs/2024-01-13")

    def test(self):
        dependency = self.dependencies["almond"]
        resource_dir = os.path.join(dependency.package_folder, dependency.cpp_info.resdirs[0])
        almond_js = os.path.join(resource_dir, "almond.js")
        test_script = os.path.join(self.source_folder, "test_almond.py")
        self.run(f'"{sys.executable}" "{test_script}" "{almond_js}"', env="conanrun")
