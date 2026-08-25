#!/usr/bin/env python3
"""Conan test recipe — DXX-Rebirth command and SDL runtime tests."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class DxxRebirthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            return
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_commands.py")
        bindir = os.path.join(dep.package_folder, "usr", "bin")
        self.run(
            f'"{sys.executable}" "{script}" "{bindir}"',
            env="conanrun",
        )
        environment = Environment()
        environment.define("SDL_VIDEODRIVER", "dummy")
        environment.define("SDL_AUDIODRIVER", "dummy")
        with environment.vars(self).apply():
            executable = os.path.join(self.cpp.build.bindirs[0], "test_sdl_runtime")
            self.run(executable, env="conanrun")
