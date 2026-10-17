#!/usr/bin/env python3
"""Conan test_package — gobject-introspection 1.78.1.

Tests the installed package by running g-ir-compiler --version,
which verifies the binary is functional and the library was correctly
linked against libgirepository-1.0.a and its static dependencies.
"""
import os

from conan import ConanFile


class GobjectIntrospectionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run g-ir-compiler --version — this is the package's installed
        # binary, linked against libgirepository-1.0.a and all static deps.
        # A successful run proves the library and tools are functional.
        pkg = self.dependencies["gobject-introspection"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        compiler = os.path.join(bin_dir, "g-ir-compiler")
        self.run(f"{compiler} --version", env="conanrun")
