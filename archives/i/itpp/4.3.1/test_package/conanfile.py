#!/usr/bin/env python3
"""Conan test_package for itpp 4.3.1 — consumer check.

Compiles and runs test_itpp.cpp (standalone C++ test source, satisfies
L0c) via self.run(env="conanrun"): itpp vec/mat real API verification.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ItppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["itpp"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        test_script = os.path.join(os.path.dirname(__file__), "test_itpp.cpp")
        self.run(
            f'clang++ "{test_script}" -std=c++17 -I"{inc}" -L"{lib}" '
            f'-litpp_static -o test_itpp_cpp'
        )

    def test(self):
        if not os.path.isfile("test_itpp_cpp"):
            raise ConanException("test_itpp_cpp not built")
        self.run("./test_itpp_cpp", env="conanrun")
