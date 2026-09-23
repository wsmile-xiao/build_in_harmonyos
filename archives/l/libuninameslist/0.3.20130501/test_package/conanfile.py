#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class LibuninameslistTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        # resolved against the reference under test (incl. user/channel)
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # cmake_layout single-config generator: consumer_tests lands
            # in the build dir root (= self.cpp.build.bindir); run it
            # directly under conanrun so the CHECK tally reaches stdout.
            executable = os.path.join(self.cpp.build.bindir, "consumer_tests")
            self.run(executable, env="conanrun")
