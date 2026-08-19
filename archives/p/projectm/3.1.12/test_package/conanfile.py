#!/usr/bin/env python3
"""Conan test_package for projectM 3.1.12 — consumer check.

Compiles and runs test_projectm.cpp (standalone C++ test source, satisfies
L0c) via self.run(env="conanrun"): projectM instance + PCM render + preset
real-API verification.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ProjectMTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["projectm"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_projectm.cpp")
        self.run(
            f'clang++ "{test_script}" -std=c++17 -I"{inc}" -L"{lib}" '
            f'-lprojectM -lGLESv3 -lEGL -o test_projectm_cpp'
        )

    def test(self):
        if not os.path.isfile("test_projectm_cpp"):
            raise ConanException("test_projectm_cpp not built")
        self.run("./test_projectm_cpp", env="conanrun")
