#!/usr/bin/env python3
"""Conan test_package for RTNeural 1.0.0 — consumer check.

Compiles and runs test_rtneural.cpp (real C++ test source, satisfies L0c):
DenseLayer real forward (weight/bias math verified) + ModelT tiny model
forward, both through the actual library API (R34).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class RTNeuralTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["rtneural"].package_folder
        inc = os.path.join(pkg, "include")
        test_script = os.path.join(os.path.dirname(__file__), "test_rtneural.cpp")
        self.run(
            f'clang++ "{test_script}" -std=c++17 -I"{inc}" '
            f'-DRTNEURAL_STL=1 -DRTNEURAL_DEFAULT_ALIGNMENT=16 '
            f'-o test_rtneural_cpp'
        )

    def test(self):
        if not os.path.isfile("test_rtneural_cpp"):
            raise ConanException("test_rtneural_cpp not built")
        self.run("./test_rtneural_cpp")
