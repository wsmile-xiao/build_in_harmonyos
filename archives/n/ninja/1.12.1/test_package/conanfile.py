#!/usr/bin/env python3
"""Conan test_package for ninja 1.12.1.

Tests that the ninja binary is functional by running --version
and building a simple project with a build.ninja file.
Uses the full path from the conan package to ensure genuine dependency.
"""
import os

from conan import ConanFile


class NinjaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the full path to the ninja binary from the conan package
        bin_dir = os.path.join(self.dependencies["ninja"].package_folder, "bin")
        ninja_bin = os.path.join(bin_dir, "ninja")
        self.output.info(f"ninja binary: {ninja_bin}")

        # Test 1: Verify version
        self.output.info("Running: ninja --version")
        self.run(f'"{ninja_bin}" --version', env="conanrun")

        # Test 2: Build a simple project using ninja
        # Create a minimal build.ninja file and run ninja on it
        build_ninja = os.path.join(self.build_folder, "build.ninja")
        with open(build_ninja, "w") as f:
            f.write(
                "rule echo\n"
                "  command = echo hello-from-ninja\n"
                "\n"
                "build hello: echo\n"
            )
        self.output.info("Running: ninja hello (build a target)")
        self.run(f'"{ninja_bin}" hello', env="conanrun")
