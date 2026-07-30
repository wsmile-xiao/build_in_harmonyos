#!/usr/bin/env python3
"""Conan test_package for makefile2graph v1.5.0 — verifies make2graph binary works.

makefile2graph is a command-line tool (not a library), so we test by:
1. Running make2graph --version to verify the binary executes
2. Piping `make -Bnd` output through make2graph to verify graph generation
"""
import os
import shutil

from conan import ConanFile


class Makefile2GraphTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        # Copy test Makefile and test.c to build folder so `make -Bnd` has something to parse
        for f in ("Makefile", "test.c"):
            src = os.path.join(self.source_folder, f)
            dst = os.path.join(self.build_folder, f)
            try:
                shutil.copy(src, dst)
            except shutil.SameFileError:
                pass

    def test(self):
        bin_dir = os.path.join(self.dependencies["makefile2graph"].package_folder, "bin")
        make2graph = os.path.join(bin_dir, "make2graph")

        # Test 1: make2graph --version (verifies binary executes correctly)
        self.run(f'"{make2graph}" --version')

        # Test 2: Pipe make -Bnd output through make2graph (functional test)
        self.run(f'make -Bnd 2>/dev/null | "{make2graph}" --format l', cwd=self.build_folder)

        # Test 3: GEXF XML output format
        self.run(f'make -Bnd 2>/dev/null | "{make2graph}" --format x', cwd=self.build_folder)
