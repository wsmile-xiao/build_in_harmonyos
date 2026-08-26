#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/gnutls/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GnutlsTestConan(ConanFile):
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
        # 把所有依赖的 lib 目录加入 LD_LIBRARY_PATH，确保运行时能找到所有库
        all_libs = []
        for dep_name in ["gnutls", "nettle", "libtasn1", "libgcrypt", "libgpg-error", "gmp", "libunistring"]:
            try:
                dep = self.dependencies[dep_name]
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    all_libs.append(lib_dir)
            except Exception:
                pass
        ld_path = ":".join(all_libs)
        harness = os.path.join(self.cpp.build.bindirs[0], "test_gnutls")
        self.run(f"LD_LIBRARY_PATH={ld_path}:$LD_LIBRARY_PATH {harness}")
