#!/usr/bin/env python3
"""Conan consumer test recipe for blosc2 3.2.3."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Blosc2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        if not can_run(self):
            self.output.info("Skipping test_blosc2: target binary cannot run here")
            return
        exe = os.path.join(self.build_folder, "test_blosc2")
        if str(self.settings.os) == "OHOS":
            shell = os.environ.get("CONFIG_SHELL") or "/system/bin/sh"
            self.run(f"{shlex.quote(shell)} -c {shlex.quote(shlex.quote(exe))}",
                     env="conanrun")
        else:
            self.run(shlex.quote(exe), env="conanrun")

