#!/usr/bin/env python3
"""Conan test_package — tidy-html5 5.8.0 L1 smoke test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TidyHtml5TestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution; other platforms run the ELF directly.
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} -c './test_tidy'", env="conanrun")
        else:
            self.run("./test_tidy", env="conanrun")
