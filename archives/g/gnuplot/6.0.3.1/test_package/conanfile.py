#!/usr/bin/env python3
"""Conan test_package for gnuplot 6.0.3.1 — L1 test.

Verifies that the gnuplot binary is installed, can report its version,
and can generate a PNG image file (gd-based image terminal support).
gnuplot is a command-line plotting tool (application), not a library.
"""
import os

from conan import ConanFile


class GnuplotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 1. Smoke test: verify the binary works
        self.run("gnuplot --version", env="conanrun")

        # 2. Functional test: generate a PNG image (requires gd support)
        png_path = os.path.join(self.build_folder, "test_output.png")
        self.run(
            f'gnuplot -e "set terminal png; set output \'{png_path}\'; plot sin(x)"',
            env="conanrun",
        )
        # Verify the PNG file was created and is non-empty
        assert os.path.exists(png_path), "PNG output file was not created"
        assert os.path.getsize(png_path) > 0, "PNG output file is empty"
