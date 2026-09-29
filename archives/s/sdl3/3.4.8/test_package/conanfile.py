#!/usr/bin/env python3
"""Conan test_package for sdl3 3.4.8 — L1 test.

Builds a test program against the installed sdl3 package, runs it on the
device (this is an OpenHarmony target build), and verifies:
  - runtime SDL version matches the packaged headers
  - SDL_InitSubSystem(SDL_INIT_EVENTS) / SDL_Quit work
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class Sdl3TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            environment = Environment()
            # Headless-safe defaults for CI workers without a display.
            environment.define("SDL_VIDEODRIVER", "dummy")
            environment.define("SDL_AUDIODRIVER", "dummy")
            with environment.vars(self).apply():
                executable = os.path.join(
                    self.cpp.build.bindirs[0], "test_sdl3")
                self.run(executable, env="conanrun")
