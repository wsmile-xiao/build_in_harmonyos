#!/usr/bin/env python3
"""Run the upstream compilation case and an OpenAL null-backend consumer."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OpenalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "upstream_basic"), env="conanrun")
        self.run(
            os.path.join(bindir, "test_openal_null_backend"),
            env="conanrun",
        )
