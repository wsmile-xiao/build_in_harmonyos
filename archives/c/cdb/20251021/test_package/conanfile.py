#!/usr/bin/env python3
"""Conan test_package for cdb — verifies command-line tools work.

Tests the cdb workflow: create a database, query it.
"""
import os

from conan import ConanFile


class CdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the bin directory from the cdb package
        bin_dir = os.path.join(self.dependencies["cdb"].package_folder, "bin")
        cdbmake = os.path.join(bin_dir, "cdbmake")
        cdbget = os.path.join(bin_dir, "cdbget")

        cdb_file = os.path.join(self.build_folder, "test.cdb")
        tmp_file = os.path.join(self.build_folder, "test.tmp")

        # Create a simple cdb database with cdbmake
        # cdbmake input format: +klen,dlen:key->data\n, terminated by empty line
        self.run(
            f'printf "+3,5:one->Hello\\n\\n" | "{cdbmake}" "{cdb_file}" "{tmp_file}"'
        )
        # Retrieve the value with cdbget
        self.run(
            f'"{cdbget}" one < "{cdb_file}"'
        )
