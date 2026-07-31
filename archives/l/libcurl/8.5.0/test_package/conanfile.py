#!/usr/bin/env python3
"""Conan test_package — libcurl 8.5.0 L1 smoke test."""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout


class LibcurlTestConan(ConanFile):
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
            bash = (os.environ.get("HNP_BASH")
                    or os.environ.get("CONFIG_SHELL")
                    or shutil.which("bash"))
            if not bash:
                raise ConanInvalidConfiguration(
                    "OHOS test_package requires bash (set HNP_BASH or CONFIG_SHELL env, "
                    "or ensure bash is on PATH)")
            self.run(f"{bash} -c './test_libcurl'", env="conanrun")
        else:
            self.run("./test_libcurl", env="conanrun")
