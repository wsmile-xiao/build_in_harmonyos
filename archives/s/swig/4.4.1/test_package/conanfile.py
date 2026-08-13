#!/usr/bin/env python3
"""Conan test_package — swig 4.4.1

Tests the swig binary by:
1. Running 'swig -version' to verify the binary works
2. Using swig to generate a Python wrapper from an interface file
3. Verifying the generated wrapper code exists

swig is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class SwigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["swig"].cpp_info.bindirs[0]
        swig_bin = os.path.join(bin_dir, "swig")

        # Test 1: Verify swig -version works
        self.run(f'"{swig_bin}" -version', env="conanrun")

        # Test 2: Use swig to generate Python wrapper code from an interface file
        # This is a substantive test (R34) — actually exercises swig's core functionality
        test_dir = os.path.dirname(__file__)
        iface = os.path.join(test_dir, "test.i")
        out_dir = self.build_folder
        self.run(f'"{swig_bin}" -python -o "{os.path.join(out_dir, "test_wrap.c")}" "{iface}"', env="conanrun")

        # Test 3: Verify the generated wrapper file exists and is non-empty
        wrap_file = os.path.join(out_dir, "test_wrap.c")
        if not os.path.isfile(wrap_file):
            raise Exception("swig did not generate test_wrap.c")
        if os.path.getsize(wrap_file) == 0:
            raise Exception("swig generated an empty test_wrap.c")
        self.output.info(f"Generated wrapper: {wrap_file} ({os.path.getsize(wrap_file)} bytes)")
