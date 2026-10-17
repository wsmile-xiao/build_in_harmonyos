#!/usr/bin/env python3
"""Conan consumer test for mjson 1.2.7."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class MjsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = os.path.realpath(executables.get("c", ""))
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                raise ConanException(
                    f"OHOS SDK linker runtime not found in active toolchain: {llvm_lib}"
                )
            environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        if not self.conf.get("tools.build:skip_test", default=False):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_mjson"))
