#!/usr/bin/env python3
"""Conan test_package — libyang 5.8.6 consumer test.

Builds a C99 consumer against the installed libyang and runs it.  The consumer
walks the whole pipeline — context, inline YANG module, JSON instance data,
validation — and checks that invalid data is actually rejected (see
src/test_libyang.c).

The package folder is also passed in as a compile definition: libyang needs a
directory containing its own YANG modules (upstream ships them in modules/ and
installs them under share/yang/modules/libyang), and ly_ctx_new() fails without
it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibyangTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        dependency = self.dependencies[self.tested_reference_str]
        modules_dir = os.path.join(
            dependency.package_folder, "share", "yang", "modules", "libyang")

        cmake = CMake(self)
        cmake.configure(variables={"LIBYANG_MODULES_DIR": modules_dir})
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libyang")
        self.run(test_bin, env="conanrun")
