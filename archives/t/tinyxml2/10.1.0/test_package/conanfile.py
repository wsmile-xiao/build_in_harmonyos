#!/usr/bin/env python3
"""Conan consumer test for tinyxml2 10.1.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Tinyxml2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: compile and link checks passed")
            return
        executable = os.path.join(self.cpp.build.bindir, "test_tinyxml2")
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} -c "{executable}"', env="conanrun")
        else:
            self.run(executable, env="conanrun")
