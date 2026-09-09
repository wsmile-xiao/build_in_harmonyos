#!/usr/bin/env python3
"""Conan test_package — rtaudio 6.0.1 consumer verification (L1, OHOS dummy boundary)."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RtaudioTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_rtaudio')}", env="conanrun")
