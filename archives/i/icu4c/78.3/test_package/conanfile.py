#!/usr/bin/env python3
"""Conan test_package for icu4c 78.3.

Two consumers run on the device: a C++ program against the packaged static
libraries, and a shell audit of the package layout.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class Icu4cTestConan(ConanFile):
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
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host: skip test")
            return
        # OHOS /system/bin/sh is mksh, which cannot exec ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise ConanException(
                "bash is required to execute the test binaries on OHOS; "
                "set CONFIG_SHELL or install bash")

        binary = os.path.join(self.cpp.build.bindirs[0], "test_icu4c")
        self.run(f"{bash} -c '{binary}'", env="conanrun")

        package_folder = self.dependencies["icu4c"].package_folder
        script = os.path.join(self.recipe_folder, "test_package_artifacts.sh")
        self.run(f"{bash} {script} '{package_folder}'", env="conanrun")
