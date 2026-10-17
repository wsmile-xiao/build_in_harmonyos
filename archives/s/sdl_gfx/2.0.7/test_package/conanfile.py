#!/usr/bin/env python3
"""test_package for sdl_gfx — L1 consumer test.

Builds test_sdl_gfx.c against the packaged headers + libSDL_gfx.a (through
CMakeDeps) and asserts pixel-level results of the drawing primitives, the
rotozoom transforms, the framerate manager and the image-filter C path.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SdlGfxTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_sdl_gfx")
        # Headless OHOS sandbox: use SDL's dummy video driver (the assertions only
        # need software surfaces).
        self.run(f'SDL_VIDEODRIVER=dummy "{exe}"', env="conanrun")
