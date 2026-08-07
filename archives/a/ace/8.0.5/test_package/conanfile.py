#!/usr/bin/env python3
"""Conan test_package — ace/8.0.5 consumer test (C++).

Calls real ACE APIs (ACE_OS::getpid, ACE_VERSION, ACE_Message_Block).
"""
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class AceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                shlex.join(
                    [
                        "ctest",
                        "--test-dir",
                        self.build_folder,
                        "--output-on-failure",
                        "--no-tests=error",
                    ]
                ),
                env="conanrun",
            )
