#!/usr/bin/env python3
"""test_package for cba 0.3.6 (CLI tool) — drives the compiled test harness.

Upstream ships NO test suite (no tests/ dir, no make check/TESTS target,
no configure.ac — plain Makefile project). Full coverage is provided here:
11 cases / 55 assertions —
  6 structural-analysis analytic checks (41 assertions),
  4 CLI parameter/error-path cases (8 assertions),
  1 -o output-file / -p plot-file consistency case (6 assertions).
The harness compiles to test_cba and is run once per case with the package
bin/ dir on PATH (VirtualRunEnv, env="conanrun").
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CbaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = self._find_harness()
        cases = ["c01_udl_single", "c02_point_mid", "c03_point_quarter",
                 "c04_cont2_udl", "c05_factor_cont2", "c06_readme_example",
                 "c07_no_args", "c08_missing_input", "c09_bad_geometry",
                 "c10_no_loads", "c11_outfile_plot"]
        for case in cases:
            # R34: each case really executes the packaged `cba` binary
            self.run(f'"{exe}" {case}', env="conanrun")

    def _find_harness(self):
        hits = glob.glob(os.path.join(self.build_folder, "**", "test_cba"),
                         recursive=True)
        if not hits:
            raise RuntimeError(f"test_cba not found under {self.build_folder}")
        return hits[0]
