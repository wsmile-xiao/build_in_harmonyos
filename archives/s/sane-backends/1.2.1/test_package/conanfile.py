#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/sane-backends/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy, save


class SanebackendsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        config_dir = os.path.join(self.build_folder, "sane.d")
        os.makedirs(config_dir, exist_ok=True)
        package_folder = self.dependencies["sane-backends"].package_folder
        copy(
            self,
            "test.conf",
            src=os.path.join(package_folder, "etc", "sane.d"),
            dst=config_dir,
        )
        save(self, os.path.join(config_dir, "dll.conf"), "test\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if os.getenv("SANE_RUN_TARGET_TESTS") == "1" and can_run(self):
            config_dir = os.path.join(self.build_folder, "sane.d")
            self.run(f"SANE_CONFIG_DIR={config_dir} ctest --output-on-failure", cwd=self.cpp.build.bindir)
        else:
            self.output.info("Set SANE_RUN_TARGET_TESTS=1 on a deployed target to run the consumer test")
