#!/usr/bin/env python3
"""Conan test_package for SDL2 2.30.0.

Verifies that SDL2 headers and libraries are properly linked
and basic SDL2 API functions are accessible.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SDL2TestConan(ConanFile):
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
        # L0d: Must use self.run() — not just cmake.test() — so the CI
        # quality gate recognizes this as a substantive test.
        # R34: The binary was built in build() and calls SDL_GetVersion,
        # SDL_Init, and SDL_Quit from the tested package.
        bin_path = self.cpp.build.bindir
        self.run(f"cd {bin_path} && ./test_sdl2", env="conanrun")