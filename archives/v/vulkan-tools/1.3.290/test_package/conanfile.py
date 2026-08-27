#!/usr/bin/env python3
"""Conan test_package for vulkan-tools 1.3.290.

Builds and runs test.c which executes vulkaninfo --summary (R34).
Also verifies the Mock ICD shared library and JSON manifest exist.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VulkanToolsTestConan(ConanFile):
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
        # Verify artifacts exist
        dep = self.dependencies["vulkan-tools"]
        bin_dir = dep.cpp_info.bindirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        res_dir = dep.cpp_info.resdirs[0] if dep.cpp_info.resdirs else ""

        vulkaninfo = os.path.join(bin_dir, "vulkaninfo")
        mock_icd_lib = os.path.join(lib_dir, "libVkICD_mock_icd.so")
        mock_icd_json = os.path.join(res_dir, "VkICD_mock_icd.json")

        assert os.path.isfile(vulkaninfo), \
            f"vulkaninfo binary not found at {vulkaninfo}"
        assert os.path.isfile(mock_icd_lib), \
            f"Mock ICD library not found at {mock_icd_lib}"
        assert os.path.isfile(mock_icd_json), \
            f"Mock ICD JSON not found at {mock_icd_json}"

        # Run compiled test (executes vulkaninfo via popen)
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_vulkan-tools")
        self.run(f'"{test_exe}"', env="conanrun")
