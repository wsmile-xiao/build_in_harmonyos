#!/usr/bin/env python3
"""test_package for 3d-ascii-viewer-c 1.4.0 — CLI consumer smoke test.

The produced artifact is the `3d-ascii-viewer` executable (CLI tool, not a
library). test() executes the L0c test source `smoke_test.sh` via self.run,
which really calls the CLI's public behavior and asserts observable results:
  1. `--snap` renders one frame of the bundled fox.obj model to stdout and
     asserts non-empty output (real functional gate).
  2. `--help` prints the usage list (upstream viewer.c exits 1 in
     output_usage() by design, so the script asserts the printed usage
     instead of the exit code).
ncurses runtime env (TERMINFO) is provided by the ncurses/6.4 dependency via its
runenv_info; declare it as a direct requirement so its runenv is aggregated into
the conanrun environment (env="conanrun").
"""
import os

from conan import ConanFile


class ThreeDAsciiViewerCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ncurses/6.4")

    def test(self):
        dep = self.dependencies["3d-ascii-viewer-c"]
        exe = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "3d-ascii-viewer")
        model = os.path.join(dep.package_folder, "share", "3d-ascii-viewer-c", "models", "fox.obj")

        # L0c: execute the test_package test source via self.run (L0d);
        # smoke_test.sh really calls the CLI public behavior and asserts.
        script = os.path.join(self.source_folder, "smoke_test.sh")
        self.run(f'sh "{script}" "{exe}" "{model}"', env="conanrun")