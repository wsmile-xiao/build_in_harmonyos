#!/usr/bin/env python3
"""test_package for perceptualdiff - consumer side L1 test.

Builds a consumer program that links the packaged ``pdiff`` library through the
exported CMake target and runs both the probe and the packaged
``perceptualdiff`` CLI.

can_run() gating is deliberately not used here: the OHOS profile pins
``tools.build.cross_building:can_run=False``, which would silently skip the
execution and produce a false green build.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class PerceptualdiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        probe = os.path.join(self.cpp.build.bindirs[0], "test_probe")
        self.run('"%s"' % probe, env="conanrun")

        package_folder = self.dependencies[self.tested_reference_str].package_folder
        cli = os.path.join(package_folder, "bin", "perceptualdiff")
        self.run('"%s" --version' % cli, env="conanrun")
        self.run('"%s" --help' % cli, env="conanrun")
