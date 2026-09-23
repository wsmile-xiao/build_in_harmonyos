#!/usr/bin/env python3
"""test_package for kyoto-cabinet 1.2.80 on HarmonyOS PC AArch64."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KyotoCabinetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    requires = "kyoto-cabinet/1.2.80"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 27 checks in test.cpp: create/write/read/overwrite/remove/
        # iterate/reopen/persistence/invalid-path/corruption/cleanup
        # CLI smoke tests run in the parent conanfile's build() via kchashmgr.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_kyoto_cabinet")
        self.run(f'"{exe}" "{self.build_folder}"', env="conanrun")
