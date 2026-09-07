#!/usr/bin/env python3
"""Consumer test for the packaged InChI API library."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class InchiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test executable directory is unavailable")
        executable = os.path.join(bindirs[0], "test_inchi")
        if not os.path.isfile(executable):
            raise ConanException(f"test executable is missing: {executable}")
        if can_run(self):
            self.run(executable, env="conanrun")
        else:
            self.output.warning(
                "Cross build compiled and linked the InChI consumer; "
                "target execution is deferred to W3"
            )
