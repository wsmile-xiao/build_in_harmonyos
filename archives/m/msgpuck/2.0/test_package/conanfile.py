#!/usr/bin/env python3
"""Consumer test for msgpuck/2.0 (header + static library)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class MsgpuckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_msgpuck")
        self.run(f'"{exe}"', env="conanrun")
