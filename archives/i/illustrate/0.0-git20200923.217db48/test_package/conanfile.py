#!/usr/bin/env python3
"""Conan test_package for illustrate — consumer verification.

Drives the installed `illustrate` binary through test_illustrate.sh: a
four-atom PDB scene is rendered with the command-card grammar documented
in the upstream README, and the script asserts the atom count echoed by
the program, the normal Fortran STOP completion marker, the P3 PNM header
with the requested dimensions, that the molecule is actually drawn
(non-background pixels present) and that the opacity companion image is
written.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IllustrateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def build(self):
        # The scene files are written by the test script into the build
        # folder, never the source tree: the recipe folder is the CI-read
        # source of truth and must stay free of generated files (CI JC4
        # junk check).  illustrate also writes its output PNM plus a fixed
        # opacity.pnm into the current working directory, so running the
        # test from the build folder keeps those side effects contained.
        os.makedirs(self.build_folder, exist_ok=True)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["illustrate"]
        bin_path = os.path.join(dep.cpp_info.bindirs[0], "illustrate")
        script = os.path.join(self.source_folder, "test_illustrate.sh")
        self.run(
            f'sh "{script}" "{bin_path}" "{self.build_folder}"',
            env="conanrun",
        )
