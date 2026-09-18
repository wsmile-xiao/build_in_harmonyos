#!/usr/bin/env python3
"""Conan test_package for zpl 9.8.0 — real consumer compile+link+run.

zpl is a single-header library: consumers define ZPL_IMPLEMENTATION in exactly
ONE source file before including <zpl.h>. This test_package compiles a
consumer program that exercises several public zpl APIs (base64 round-trip,
string build, hash), asserts observable results and prints them, then runs it.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ZplTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if can_run(self):
            self.run("./test_zpl", env="conanrun")
