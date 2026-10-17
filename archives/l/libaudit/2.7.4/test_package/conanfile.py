#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class LibauditTestConan(ConanFile):
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
            # run the consumer contract test directly under conanrun
            executable = os.path.join(self.cpp.build.bindirs[0],
                                      "consumer_tests")
            self.run(executable, env="conanrun")
