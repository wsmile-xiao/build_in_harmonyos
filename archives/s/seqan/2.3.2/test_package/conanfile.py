#!/usr/bin/env python3
"""Conan test_package for seqan 2.3.2 (header-only C++ library).

Uses C++14 because SeqAn 2.3.2 predates C++17: in C++17 mode libc++'s
std::empty() participates in ADL and becomes ambiguous with seqan::empty()
used inside <seqan/system/file_sync.h>.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SeqanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    # SeqAn 2.3.2 requires C++14 (C++17 makes std::empty ambiguous)
    default_options = {"*:cxxstd": "14"}

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the compiled test binary that exercises SeqAn APIs (R34)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_seqan")
        self.run(bin_path, env="conanrun")
