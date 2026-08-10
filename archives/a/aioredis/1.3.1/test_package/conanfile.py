#!/usr/bin/env python3
"""test_package for aioredis — validates Python source files."""
import os

from conan import ConanFile


class AioredisTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["aioredis"]
        test_script = os.path.join(self.source_folder, "test_aioredis.py")
        self.run(f'python3 "{test_script}" "{dep.package_folder}"', env="conanrun")
