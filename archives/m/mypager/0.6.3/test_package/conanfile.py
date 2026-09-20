#!/usr/bin/env python3
"""Conan test_package for mypager — consumer-side behaviour test.

mypager is a pager script executed with the system perl.  The consumer
runs the packaged script with --help (asserts usage output and exit 0)
and pipes a small text file through it (a file shorter than one page
must pass through with its content intact).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MypagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["mypager"]
        script = os.path.join(dep.package_folder, "bin", "mypager")
        consumer = os.path.join(self.cpp.build.bindirs[0], "dd_consumer")
        # hnp perl first in PATH so the /usr/bin/env perl shebang resolves.
        self.run(
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'MYPAGER_SCRIPT="{script}" "{consumer}"')
