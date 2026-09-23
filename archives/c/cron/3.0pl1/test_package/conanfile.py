#!/usr/bin/env python3
"""Conan consumer test for the cron command-line tools."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cron_package = self.dependencies["cron"].package_folder
        cron_path = os.path.join(cron_package, "bin", "cron")
        bindir = self.cpp.build.bindirs[0]
        test_path = os.path.join(bindir, "test_cron")
        ohos_test_path = os.path.join(bindir, "test_cron_ohos")
        self.run(f'CRON_BIN="{cron_path}" "{test_path}"', env="conanrun")
        self.run(f'CRON_BIN_OHOS="{cron_path}" "{ohos_test_path}"', env="conanrun")
