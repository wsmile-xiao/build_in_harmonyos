#!/usr/bin/env python3
"""Conan test package for libsee 1.1.0 (CMake and preload consumers)."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibseeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        from conan.tools.cmake import CMakeDeps, CMakeToolchain
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if self.conf.get("tools.build:skip_test", default=False):
            return
        self.run(self.cpp.build.bindirs[0] + "/libsee_consumer", env="conanrun")

        # Exercise the package's core LD_PRELOAD path with the OHOS shell.
        libsee = os.path.join(self.dependencies["libsee"].package_folder, "lib", "libsee.so")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        command = "LD_PRELOAD={} {} -c true".format(
            shlex.quote(libsee), shlex.quote(bash)
        )
        self.run(command, env="conanrun")
