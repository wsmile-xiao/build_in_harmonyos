#!/usr/bin/env python3
"""Conan test_package for libfishsound 1.0.1 — Conan L1 official test.

Compiles the consumer round-trip test against the packaged library and
runs the binary directly (CI L0c expects an explicit self.run()).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibfishsoundTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Patch CMake toolchain for local dev (CI has /data/service/hnp/bin/)
        if not os.path.exists("/data/service/hnp/bin/bash"):
            clang_path = shutil.which("clang") or "clang"
            clangxx_path = shutil.which("clang++") or "clang++"
            toolchain_path = os.path.join(
                self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(toolchain_path):
                with open(toolchain_path, "r") as f:
                    content = f.read()
                if "/data/service/hnp/bin/" in content:
                    content = content.replace(
                        "/data/service/hnp/bin/clang++", clangxx_path)
                    content = content.replace(
                        "/data/service/hnp/bin/clang", clang_path)
                    with open(toolchain_path, "w") as f:
                        f.write(content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0],
                                    "test_libfishsound")
            self.run(test_bin, env="conanrun")
