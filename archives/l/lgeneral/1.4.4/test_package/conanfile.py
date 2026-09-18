#!/usr/bin/env python3
"""Conan test recipe — lgeneral command, upstream-testfile and ELF checks."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LgeneralTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # runtime DSO chain: sdl12-compat provides libSDL-1.2.so.0 on top of SDL2
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("sdl2/2.30.10", run=True)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_commands.py")
        bindir = os.path.join(dep.package_folder, "usr", "bin")
        # headless engine startup path: dummy SDL drivers, no display needed
        environment = Environment()
        environment.define("SDL_VIDEODRIVER", "dummy")
        environment.define("SDL_AUDIODRIVER", "dummy")
        with environment.vars(self).apply():
            self.run(
                f'"{sys.executable}" "{script}" "{bindir}"',
                env="conanrun",
            )
