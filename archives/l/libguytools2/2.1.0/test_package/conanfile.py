#!/usr/bin/env python3
"""Conan test_package for libguytools2/2.1.0 - consumer functional test (CI L1).

Upstream ships no test suite at all (no tests/ directory, no test_*.cpp, no
check/test target in tools.pro), so this package provides a *functional*
consumer test instead of assertions on constants: test_libguytools2.cpp drives
the packaged library with real inputs - configuration files on disk, log files
read back from disk, real SIGHUP/SIGTERM round trips, uname()/ioctl queries -
and verifies the real results.

`conan create` compiles and executes it, so a broken package (missing symbol,
stale library, mis-parsed configuration, mis-packaged headers) fails the build
instead of passing silently.

File location: archives/{letter}/libguytools2/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class Libguytools2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _test_binary(self):
        """Path of the functional test executable built above."""
        for directory in self.cpp.build.bindirs:
            binary = os.path.join(directory, "test_libguytools2")
            if os.path.isfile(binary):
                return binary
        raise ConanException(
            "test_libguytools2 was not built into {}".format(self.cpp.build.bindirs)
        )

    def build(self):
        cmake = CMake(self)
        # The test compares the version reported by the packaged library with
        # the version of the package under test.
        cmake.configure(variables={
            "LIBGUYTOOLS2_TESTED_VERSION": self.dependencies["libguytools2"].ref.version,
        })
        cmake.build()

    def test(self):
        # Run the functional test explicitly (instead of relying on ctest only)
        # so its per-check PASS/FAIL output shows up in the CI log.
        self.run('"{}"'.format(self._test_binary()), env="conanrun")
