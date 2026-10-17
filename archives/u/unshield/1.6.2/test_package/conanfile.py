#!/usr/bin/env python3
"""Conan test_package for unshield 1.6.2 — L1 consumer test.

test() verifies that:
  1. The unshield binary is installed and reports its version (L2 smoke test).
  2. The libunshield header is available and can be compiled against.
"""
import os

from conan import ConanFile


class UnshieldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L2 smoke test: verify the binary runs and reports version
        bin_path = os.path.join(self.dependencies["unshield"].package_folder, "bin", "unshield")
        self.run(f'"{bin_path}" --version', env="conanrun")

        # R34: Verify the library API is usable — compile a tiny C program
        # that links against libunshield and calls a real function.
        inc_dir = self.dependencies["unshield"].cpp_info.includedirs[0]
        inc_path = os.path.join(self.dependencies["unshield"].package_folder, inc_dir)
        lib_dir = self.dependencies["unshield"].cpp_info.libdirs[0]
        lib_path = os.path.join(self.dependencies["unshield"].package_folder, lib_dir)

        test_src = os.path.join(os.path.dirname(__file__), "test_api.c")
        bin_name = "test_unshield_api"
        self.run(
            f"clang -I\"{inc_path}\" -L\"{lib_path}\" "
            f"{test_src} -lunshield -o {bin_name}",
            env="conanrun",
        )
        self.run(f"./{bin_name}", env="conanrun")