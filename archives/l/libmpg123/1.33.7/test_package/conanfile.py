#!/usr/bin/env python3
"""Conan test_package for libmpg123 — verifies libmpg123 API works."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Mpg123TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS: wrap with CONFIG_SHELL bash; static build means no
            # runtime .so lookup, but keep the bash wrapper for consistent
            # ELF exec semantics.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            exe = os.path.join(self.cpp.build.bindirs[0], "test_libmpg123")
            self.run(f'"{bash}" -c \'{exe}\'', env="conanrun")
        else:
            self.output.info("cross-building: compile-only consumer test")
