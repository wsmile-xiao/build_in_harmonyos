#!/usr/bin/env python3
"""Conan test_package — libsvm 3.37 L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibsvmTestConan(ConanFile):
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
        # VirtualRunEnv handles LD_LIBRARY_PATH on os=Linux (CI profile)
        # On os=OHOS, VirtualRunEnv doesn't set it, so we set it manually
        dep = self.dependencies["libsvm"]
        libdir = os.path.join(dep.package_folder, "lib")
        if libdir not in os.environ.get("LD_LIBRARY_PATH", ""):
            os.environ["LD_LIBRARY_PATH"] = libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        self.run(os.path.join(self.build_folder, "test_libsvm"), env="conanrun")
