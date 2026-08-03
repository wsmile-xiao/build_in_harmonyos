#!/usr/bin/env python3
"""Test package for WasmEdge 0.17.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WasmEdgeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_wasmedge")
            if self.settings.os == "Windows":
                test_bin += ".exe"
            if not os.path.exists(test_bin):
                raise RuntimeError(f"test_package binary not found: {test_bin}")
            for mode in (
                "--version-api",
                "--vm-lifecycle",
                "--vm-execute-add",
                "--vm-repeat-execute",
                "--reject-invalid-module",
                "--reject-missing-function",
            ):
                self.run(f'"{test_bin}" {mode}', env="conanrun")
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
