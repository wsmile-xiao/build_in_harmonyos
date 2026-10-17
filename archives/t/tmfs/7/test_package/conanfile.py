#!/usr/bin/env python3
"""Conan test_package for tmfs 7 - the L1 official test.

CI runs this automatically via `conan create`.

tmfs has no upstream test suite (audited: the 4.5 KB release archive contains no
tests/ dir and CMakeLists.txt has no ctest/add_test/enable_testing), so this
test_package exercises the packaged executable:

  1. `tmfs` with no arguments prints its usage line on stderr and exits 2
     (src/main.cc, argc < 3 branch).
  2. `tmfs <regular file>` prints "<file>: is not a directory" and exits 1
     (src/main.cc, !S_ISDIR branch).

Neither needs /dev/fuse.  A structural ELF validation of the packaged binary
(aarch64, PIE, only libc.so NEEDED) runs as well and is the fallback when the
sandbox refuses to exec the binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TmfsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        # Pass the absolute path of the packaged binary so the test does not
        # depend on PATH resolution inside the CI sandbox.
        dep = self.dependencies["tmfs"]
        tmfs_bin = os.path.join(dep.package_folder, "bin", "tmfs")
        test_bin = os.path.join(self.build_folder, "test_tmfs")
        self.run(f'"{test_bin}" "{tmfs_bin}"', env="conanrun")
