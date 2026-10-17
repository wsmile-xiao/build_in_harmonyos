#!/usr/bin/env python3
"""Conan test_package — psimd 0.0-git20200517.072586a (Conan L1 official test).

Consumer test (C++): compile-time NEON backend gate + 12 API known-value
assertions (splat/add/sub/mul/min/max/abs/blend/signblend/load/store/qfma).
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/p/psimd/0.0-git20200517.072586a/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PsimdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run the consumer binary directly as well: leaves an explicit
        # execution trace in the conan create log (CI L1b evidence) and
        # doubles as belt-and-braces if the ctest wrapper misbehaves.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_psimd")
        self.run(f'"{exe}"', env="conanrun")
