#!/usr/bin/env python3
"""Conan L1 test for aiksaurus 1.2.1+dev-0.12.

R34: test must actually exercise the packaged library API.
This test builds a small C++ program that opens the thesaurus data
(meanings.dat / words.dat) shipped in the package resdirs and performs
a real synonym lookup via Aiksaurus::find() + Aiksaurus::next().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class AiksaurusTestConan(ConanFile):
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
        if can_run(self):
            # Data files live in the package's share/aiksaurus/ resdir
            dep = self.dependencies["aiksaurus"]
            data_dir = os.path.join(dep.package_folder, "share", "aiksaurus")
            meanings = os.path.join(data_dir, "meanings.dat")
            words = os.path.join(data_dir, "words.dat")
            if not (os.path.exists(meanings) and os.path.exists(words)):
                raise Exception(
                    "aiksaurus test data not found: " + data_dir
                )
            bin_path = os.path.join(self.cpp.build.bindir, "test_aiksaurus")
            self.run(f"{bin_path} {meanings} {words}", env="conanrun")
