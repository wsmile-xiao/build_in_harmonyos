#!/usr/bin/env python3
"""Conan test_package — libecpint 1.0.7.

Consumer test: find_package(ecpint CONFIG), link ECPINT::ecpint, run a
real shell-pair integral and compare it with the upstream IntTest1
benchmark (see test_ecpint.cpp). Re-emits the upstream verdicts recorded
during build() when the package comes from the Conan cache.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibecpintTestConan(ConanFile):
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
        # OHOS /system/bin/sh (mksh) cannot exec ELF directly; wrap with
        # the worker bash (ableton-link pattern).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ecpint")
        self.run(f'{bash} -c "{bin_path}"', env="conanrun")
