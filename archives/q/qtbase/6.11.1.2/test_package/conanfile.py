#!/usr/bin/env python3
"""Consume Qt through its published CMake and build/run environments."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class QtbaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        make = self.conf.get("tools.gnu:make_program", default=None)
        if make and "Makefiles" in tc.generator:
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = str(make).replace("\\", "/")
        tc.presets_build_environment = build_env.environment()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            command = [sys.executable, os.path.join(self.source_folder, "run_tests.py"),
                       "--bin-dir", os.path.abspath(self.cpp.build.bindirs[0]),
                       "--log-dir", os.path.join(self.build_folder, "consumer-logs"),
                       "--require-aarch64"]
            if os.environ.get("QTBASE_RUN_WAYLAND_TESTS") == "1":
                command.append("--wayland")
            self.run(shlex.join(command), env="conanrun")
