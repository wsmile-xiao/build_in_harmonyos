#!/usr/bin/env python3
"""Conan test_package — vkfft 1.3.4 (header-only, Vulkan backend).

L1 test: compile a real consumer TU that includes <vkFFT/vkFFT.h>
with VKFFT_BACKEND=0 (pulling in vulkan/vulkan.h and the glslang C
interface transitively) and exercises the public API structs on the
host side, then run it. Runtime device FFT is not exercised because
CI has no Vulkan GPU device — disclosed in notes.md / PR body.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VkfftTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_vkfft"),
                 env="conanrun")
