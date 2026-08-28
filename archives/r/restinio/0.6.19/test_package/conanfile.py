#!/usr/bin/env python3
"""Conan test_package — restinio 0.6.19

Consumer smoke test (API / dependency connectivity): find_package(restinio) +
restinio::restinio, verify a minimal HTTP request handler compiles and links
against the real Conan requires (fmt, http-parser) and the bundled
standalone-asio snapshot. It does NOT run a network server and does NOT cover
sendfile or end-to-end request/response round-trips.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RestinioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # fmt and http-parser are transitive requires of restinio; declare them
        # explicitly so CMakeDeps emits find_package() fragments for all three.
        self.requires("fmt/8.1.1")
        self.requires("http-parser/2.9.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "14"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "restinio_test")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            self.run(bin_path, env="conanrun")
