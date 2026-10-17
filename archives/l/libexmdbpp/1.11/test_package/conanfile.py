#!/usr/bin/env python3
"""Conan test_package — libexmdbpp 1.11 consumer-level verification.

CI runs this automatically via `conan create`. The binary really executes the
public API of the packaged shared library (see test.cpp) and exits non-zero on
the first failed CHECK.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibexmdbppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Same OHOS trap as in the recipe: keep compiler output on disk, not on a pipe.
        build_log = os.path.join(self.build_folder, "build.log")
        try:
            with open(build_log, "w") as log:
                cmake.build(stdout=log, stderr=log)
        except ConanException:
            if os.path.isfile(build_log):
                with open(build_log) as log:
                    self.output.error(log.read()[-4000:])
            raise

    def test(self):
        # Run the consumer test binary with the conanrun environment so that the
        # just-built libexmdbpp.so is resolved through LD_LIBRARY_PATH.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libexmdbpp")
        self.run(bin_path, env="conanrun")
