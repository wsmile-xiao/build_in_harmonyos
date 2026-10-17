#!/usr/bin/env python3
"""test_package for libraw — L1 Conan test (R34: substantive API call).

Compiles a small C program that links against libraw and calls the real
LibRaw C API (libraw_init / libraw_open_buffer / libraw_strerror /
libraw_version / libraw_recycle / libraw_close).  The program is run on
the OHOS aarch64 host to verify the library links and the symbols resolve.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrawTestConan(ConanFile):
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
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        # Run the test executable directly via self.run() so the L0d gate
        # detects an actual test invocation (cmake.test() is not recognized).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libraw")
        self.run(exe, env=["LD_LIBRARY_PATH"])
