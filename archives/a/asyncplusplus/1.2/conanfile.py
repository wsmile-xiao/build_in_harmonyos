#!/usr/bin/env python3
"""Conan recipe — asyncplusplus 1.2

Async++ is a lightweight concurrency framework for C++11/14.
Provides task scheduling, continuations, parallel_for, parallel_invoke, etc.

Build system: CMake
License: MIT
Homepage: https://github.com/Amanieu/asyncplusplus

OHOS adaptations:
  - cmake_minimum_required bumped from 3.1 to 3.5 (CMake 4.x compat)
  - BUILD_SHARED_LIBS=OFF (static library for Conan packaging)
  - USE_CXX_EXCEPTIONS=ON (default, keep exception support)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class AsyncplusplusConan(ConanFile):
    name = "asyncplusplus"
    version = "1.2"
    description = "A lightweight concurrency framework for C++11/14"
    license = "MIT"
    homepage = "https://github.com/Amanieu/asyncplusplus"
    url = "https://github.com/Amanieu/asyncplusplus"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_cmake_minimum(self):
        """Bump cmake_minimum_required from 3.1 to 3.5 for CMake 4.x compat."""
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        content = open(cmakelists, "r", encoding="utf-8").read()
        patched = content.replace(
            "cmake_minimum_required(VERSION 3.1)",
            "cmake_minimum_required(VERSION 3.5)",
        )
        if patched != content:
            open(cmakelists, "w", encoding="utf-8").write(patched)
            self.output.info("Patched cmake_minimum_required: 3.1 -> 3.5")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["USE_CXX_EXCEPTIONS"] = True
        tc.generate()

    def build(self):
        self._patch_cmake_minimum()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # NOTE: upstream repo has no test suite (no tests/ dir, no CTest targets)
        # Testing is covered by test_package (Conan L1)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["async++"]
        # async++ uses its own cmake config (Async++Config.cmake)
        self.cpp_info.set_property("cmake_file_name", "Async++")
        self.cpp_info.set_property("cmake_target_name", "Async++")
