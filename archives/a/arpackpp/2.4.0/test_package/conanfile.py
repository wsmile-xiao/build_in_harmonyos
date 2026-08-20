#!/usr/bin/env python3
"""Conan test_package for arpackpp 2.4.0.

L1 test: verifies that arpack++ headers compile and the ARPACK++
C++ API can solve a real symmetric eigenvalue problem.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout


class ArpackppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # Use subprocess directly (conan self.run() breaks cmake try-compile on OHOS)
        for var in ["CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS",
                     "CMAKE_PREFIX_PATH", "MAKEFLAGS", "MFLAGS"]:
            os.environ.pop(var, None)
        os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
        build_dir = self.build_folder
        generators_dir = os.path.join(build_dir, "generators")
        toolchain = os.path.join(generators_dir, "conan_toolchain.cmake")
        r = subprocess.run(
            ["cmake", "-G", "Unix Makefiles",
             f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
             "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
             "-DCMAKE_BUILD_TYPE=Release",
             self.source_folder],
            cwd=build_dir, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("CMAKE STDERR:", r.stderr[-3000:])
            raise RuntimeError(f"cmake configure failed ({r.returncode})")
        r = subprocess.run(
            ["cmake", "--build", ".", "-j1"],
            cwd=build_dir, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("BUILD STDERR:", r.stderr[-3000:])
            raise RuntimeError(f"cmake build failed ({r.returncode})")

    def test(self):
        # Use self.run() which sets up conan run environment (LD_LIBRARY_PATH etc)
        test_exe = os.path.join(self.build_folder, "test_arpackpp")
        self.run(test_exe, env="conanrun")
