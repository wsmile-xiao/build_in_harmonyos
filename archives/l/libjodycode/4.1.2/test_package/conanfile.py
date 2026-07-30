#!/usr/bin/env python3
"""Conan test_package for libjodycode 4.1.2."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibjodycodeTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: compile and link validation only")
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libjodycode")
        if self.settings.os == "OHOS":
            bash = self._test_shell()
            self.run(f'{bash} -c "{test_bin}"', env="conanrun")
        else:
            self.run(test_bin, env="conanrun")

    def _test_shell(self):
        shell = os.environ.get("CONFIG_SHELL")
        if shell and (not os.path.isabs(shell) or os.path.exists(shell)):
            return shell
        return shutil.which("bash") or "bash"
