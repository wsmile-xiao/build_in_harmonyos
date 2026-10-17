#!/usr/bin/env python3
"""L1 test package for libxdp/1.6.3 (consumer view)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxdpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test.c includes <xdp/libxdp.h>, which includes <bpf/libbpf.h>;
        # declare libbpf directly so its include dirs are generated for this
        # consumer (the same dependency libxdp itself propagates).
        self.requires("libbpf/1.5.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the built consumer binary explicitly (CI L0d requires self.run).
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libxdp"),
                 env="conanrun")
