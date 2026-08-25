#!/usr/bin/env python3
"""Conan test_package for libselinux 3.10.1 — consumer verify."""
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
import os


class LibselinuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only check passed")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c ./test_package", env="conanrun")