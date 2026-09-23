#!/usr/bin/env python3
import os
from conan import ConanFile

class MandbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["man-db"]
        man_bin = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "man")
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {test_sh} {man_bin}", env="conanrun")
