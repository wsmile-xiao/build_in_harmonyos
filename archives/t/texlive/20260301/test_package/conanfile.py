#!/usr/bin/env python3
"""Conan test_package for texlive — L1 official test.

Tests that texlive binaries are installed and functional:
1. tex --version (plain TeX engine)
2. pdftex --version (pdfTeX engine)
3. pdflatex PDF generation (full LaTeX pipeline)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TexliveTestConan(ConanFile):
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
        # R34: test must actually exercise the package
        # Run the test binary which calls tex and pdftex
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_texlive")
        self.run(test_bin, env="conanrun")
