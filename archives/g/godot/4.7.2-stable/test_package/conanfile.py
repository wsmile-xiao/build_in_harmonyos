#!/usr/bin/env python3
"""Conan test recipe — Godot engine command + embedded doctest validation."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GodotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dep.package_folder, "bin", "godot")
        script = os.path.join(self.recipe_folder, "test_runner.py")

        # Drive the installed engine binary through its real consumer paths:
        # --version (boot), --help (parser), --test (embedded doctest suite;
        # default group, three OHOS environment-limited cases excluded —
        # /tmp-hardcoded ConfigFile+UDSServer [OHOS read-only /tmp, E002]
        # and musl IPv6 resolver [IP]; see notes.md experiment 12).
        self.run(
            f'"{sys.executable}" "{script}" "{binary}"',
            env="conanrun",
        )
