#!/usr/bin/env python3
"""Conan test_package for libfastjson — consumer round-trip test (R34: real API).

Uses direct clang invocation (same pattern as libestr test_package) to avoid
HMDFS permission issues with CMake's find_library (E046).
"""
import os

from conan import ConanFile


class LibfastjsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Get include and lib paths directly from the dependency package
        deps = self.dependencies["libfastjson"]
        inc = os.path.join(deps.package_folder, "include")
        lib = os.path.join(deps.package_folder, "lib")

        cc = os.environ.get("CC", "clang")
        # libfastjson installs headers into include/libfastjson/*.h
        # and libfastjson.so / libfastjson.a into lib/
        self.run(f'{cc} -fPIC -O2 -I"{inc}" test.c -o test_libfastjson -L"{lib}" -lfastjson')

    def test(self):
        self.run("./test_libfastjson", env="conanrun")
