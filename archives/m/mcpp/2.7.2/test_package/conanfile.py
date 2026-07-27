#!/usr/bin/env python3
"""Conan test package for the libmcpp API and mcpp CLI."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load, save


class McppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise AssertionError("test executable directory is unavailable")

        test_bin = os.path.join(bindirs[0], "test_mcpp")
        test_result = self.run(
            f'"{test_bin}"',
            env="conanrun",
            cwd=self.build_folder,
            ignore_errors=True,
        )
        if test_result != 0:
            raise AssertionError(f"test_mcpp exited with {test_result}")

        mcpp_bin = os.path.join(
            self.dependencies["mcpp"].package_folder, "bin", "mcpp"
        )
        input_path = os.path.join(self.build_folder, "mcpp_cli_input.c")
        output_path = os.path.join(self.build_folder, "mcpp_cli_output.i")
        save(
            self,
            input_path,
            "#define MCPP_CLI_TOKEN 271828\nint mcpp_cli_value = MCPP_CLI_TOKEN;\n",
        )
        cli_result = self.run(
            f'"{mcpp_bin}" -P "{input_path}" -o "{output_path}"',
            env="conanrun",
            ignore_errors=True,
        )
        if cli_result != 0:
            raise AssertionError(f"mcpp CLI exited with {cli_result}")
        cli_output = load(self, output_path)
        if "271828" not in cli_output or "MCPP_CLI_TOKEN" in cli_output:
            raise AssertionError("mcpp CLI did not expand MCPP_CLI_TOKEN")
