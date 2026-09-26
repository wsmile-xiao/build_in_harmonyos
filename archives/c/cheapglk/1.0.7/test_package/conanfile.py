#!/usr/bin/env python3
"""Conan test_package — cheapglk 1.0.7 consumer test.

Consumer 视角: find_package(cheapglk) + cheapglk::cheapglk，验证 Glk API。
交叉编译(Windows 宿主 -> OHOS armv8)时用 qemu-aarch64 运行测试二进制。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CheapGlkTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_cheapglk")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            self.run(bin_path, env="conanrun")