#!/usr/bin/env python3
"""Consumer tests for the SDL_mixer 1.2.12 package."""

import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class SdlMixerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sdl12-compat/1.2.68")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("SDL_mixer runtime tests require an executable HarmonyOS test environment")
        environment = Environment()
        environment.define("SDL_VIDEODRIVER", "dummy")
        environment.define("SDL_AUDIODRIVER", "dummy")
        with environment.vars(self).apply():
            for executable in ("test_sdl_mixer_api", "test_sdl_mixer_ohos"):
                self.run(os.path.join(self.cpp.build.bindirs[0], executable), env="conanrun")
