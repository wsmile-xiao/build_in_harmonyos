#!/usr/bin/env python3
"""Conan test_package for libhugetlbfs 2.24 — consumer contract test.

NOTE (W0/W1): this validates the installed-package consumer contract — link
libhugetlbfs and query page sizes through hugetlbfs.h. It CANNOT run on
HarmonyOS because the package itself is blocked at platform level (no
hugetlbfs backend; conanfile.py raises ConanInvalidConfiguration on os=OHOS).
It is provided as the intended consumer test for the Linux path; see notes.md.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibhugetlbfsTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_libhugetlbfs'", env="conanrun")
