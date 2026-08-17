#!/usr/bin/env python3
"""Conan test_package for qttools 6.11.1 — verify CMake and lrelease."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QttoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Keep qtbase directly visible so the test can select its native Qt6
        # config alongside the separately packaged Qt6LinguistTools config.
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        qttools_prefix = self.dependencies["qttools"].package_folder
        qtbase_prefix = self.dependencies["qtbase"].package_folder

        tc = CMakeToolchain(self)
        tc.cache_variables["QTTOOLS_PREFIX"] = qttools_prefix
        tc.cache_variables["QTBASE_PREFIX"] = qtbase_prefix
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            (qttools_prefix, qtbase_prefix)
        )
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools_prefix, "lib", "cmake", "Qt6LinguistTools"
        )
        # Qt6Config's dependency chain calls _qt_internal_find_host_info_package
        # which, when QT_REQUIRE_HOST_PATH_CHECK is on, looks for a separate
        # Qt6HostInfo package — that only exists for cross-compiled Qt setups.
        # The test runs natively on OHOS, so skip the host-info check.
        tc.cache_variables["QT_REQUIRE_HOST_PATH_CHECK"] = "FALSE"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
        )
