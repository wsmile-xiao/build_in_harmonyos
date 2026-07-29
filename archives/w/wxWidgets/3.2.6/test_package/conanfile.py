#!/usr/bin/env python3
"""Conan test_package for wxWidgets 3.2.6 — Conan L1 official test.

Uses CMake to build the test (CMakeLists.txt already exists).
CMakeToolchain handles compiler settings automatically (R33 compliant).
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WxWidgetsTestConan(ConanFile):
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
        if self.settings.os == "OHOS":
            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} -c './test_wxwidgets'", env="conanrun")
        else:
            self.run("./test_wxwidgets", env="conanrun")
