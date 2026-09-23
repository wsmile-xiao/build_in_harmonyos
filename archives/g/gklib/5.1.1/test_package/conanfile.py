#!/usr/bin/env python3
"""Consumer test for the GKlib package."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GKlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if os.name == "nt":
            toolchain.generator = "Ninja"
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "2"])

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link checks completed")
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = Path(self.build_folder) / "bin" / f"test_gklib{suffix}"
        if not executable.is_file():
            raise ConanException(f"consumer executable not found: {executable}")
        self.run(f'"{executable.resolve()}"', env="conanrun")
