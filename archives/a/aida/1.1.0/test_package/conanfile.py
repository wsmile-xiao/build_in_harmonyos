#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/aida/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AidaTestConan(ConanFile):
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
        # Inject the LV2 plugin path from the packaged tree so dlopen() in
        # test_aida can locate AIDA-X_dsp.so regardless of CWD.
        aida_pkg = self.dependencies["aida"].package_folder
        lv2_path = os.path.join(aida_pkg, "lib", "lv2", "AIDA-X.lv2", "AIDA-X_dsp.so")
        os.environ["AIDA_LV2_PATH"] = lv2_path
        self.run(
            f"{os.path.join(self.cpp.build.bindirs[0], 'test_aida')}",
            env="conanrun",
        )
