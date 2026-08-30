#!/usr/bin/env python3
"""Conan test_package — vulkan-volk 1.4.350 consumer test.

Tests that the volk library links correctly and its API is callable.
volkInitialize() loads the Vulkan loader dynamically; on headless
systems without Vulkan it returns an error but the API is still exercised.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VulkanVolkTestConan(ConanFile):
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
        self.run("./test_volk", env="conanrun")
