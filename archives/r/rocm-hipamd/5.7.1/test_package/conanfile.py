#!/usr/bin/env python3
"""Test package — rocm-hipamd 5.7.1 (header compile/symbol assertions + artifact completeness)."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
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
        # Header-library package: verify the packaged artifacts consumers rely
        # on are complete (headers, CMake modules, helper scripts, VERSION,
        # license) before running the compile/symbol test binary.
        pkg = self.dependencies["rocm-hipamd"].package_folder
        expected = [
            "include/hip/hip_common.h",
            "include/hip/hip_runtime_api.h",
            "include/hip/hip_runtime.h",
            "include/hip/hip_vector_types.h",
            "cmake/FindHIP.cmake",
            "cmake/FindHIP/run_hipcc.cmake",
            "bin/hipcc_cmake_linker_helper",
            "bin/hipdemangleatp",
            "VERSION",
            "licenses/LICENSE.txt",
        ]
        missing = [p for p in expected if not os.path.isfile(os.path.join(pkg, p))]
        if missing:
            raise AssertionError(f"rocm-hipamd package incomplete, missing: {missing}")
        self.run("ctest --test-dir . --output-on-failure", env="conanrun")
