#!/usr/bin/env python3
"""Conan test_package for libestr — L1 smoke test (R34: calls real API).

Uses direct clang invocation instead of CMakeDeps to avoid HMDFS permission
issues with CMake's find_library (E046: files created with 640 perms are
invisible to CMake's find_library on HMDFS).
"""
import os

from conan import ConanFile


class LibestrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Get include and lib paths directly from the dependency package
        deps = self.dependencies["libestr"]
        inc = os.path.join(deps.package_folder, "include")
        lib = os.path.join(deps.package_folder, "lib")

        cc = os.environ.get("CC", "clang")
        # Compile and link the test program
        self.run(f'{cc} -fPIC -O2 -I"{inc}" test.c -o test_libestr -L"{lib}" -lestr')

    def test(self):
        self.run("./test_libestr", env="conanrun")
