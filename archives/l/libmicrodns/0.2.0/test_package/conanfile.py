"""Conan test_package — libmicrodns 0.2.0.

Compiles and runs a consumer program against the installed package: the
public headers (microdns/microdns.h, microdns/rr.h) and the packaged
libmicrodns library.

The default build is static, so the consumer binary is self-contained and
can execute natively on HarmonyOS PC CI workers (immune to the musl
dynamic linker's hard-coded search path restriction described in the
cairomm 1.16.2 notes).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmicrodnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libmicrodns")
        self.run(bin_path, env="conanbuild")
