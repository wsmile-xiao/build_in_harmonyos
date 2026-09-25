#!/usr/bin/env python3
"""test_package for simstring 1.0.

Two layers, both with real execution (PF3: no empty/pass-only test()):
  1. test_simstring — C++ consumer compiled against the packaged headers,
     exercises ngram writer/reader end to end (build DB -> retrieve) with
     explicit assertions.
  2. test.sh — CLI frontend smoke via the packaged `simstring` binary
     (-v / -b build / exact+cosine query / -h), each with output assertions.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SimstringTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) header-only API consumer with assertions (non-zero on failure)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_simstring")
        self.run(exe, env="conanrun")
        # 2) packaged CLI frontend (OHOS /system/bin/sh is toybox; use bash).
        # This package is header-library, so conan's VirtualRunEnv only runs
        # `runenv_from_cpp_info` (which prepends cpp_info.bindirs to PATH)
        # when the require has run=True — tools/env/virtualrunenv.py:79 —
        # and conanrun's generated script therefore has an empty var list:
        # a bare `simstring` fails with Error 127. Pass the bin dir as $1
        # instead (abiword-plugin-* test_package precedent; the aa3d route of
        # package_type=application was rejected: mislabeling a header library
        # as an application is worse than an explicit argument).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test.sh")
        bindir = os.path.join(self.dependencies["simstring"].package_folder, "bin")
        self.run(f'"{bash}" "{script}" "{bindir}"', env="conanrun")
