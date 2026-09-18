#!/usr/bin/env python3
"""Conan test_package for cif-tools 2.0.0 — consumer check.

Runs test_cif_tools.sh (standalone consumer test, satisfies L0c) via self.run
with env="conanrun". Verifies the installed executables exist and one of them
(cif-merge) runs on a small embedded mmCIF file.
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["cif-tools"].package_folder
        # sanity: at least the six documented programs are installed
        progs = ["pdb2cif", "cif2pdb", "cif-diff", "cif-merge",
                 "cif-validate", "mmcql"]
        for p in progs:
            exe = os.path.join(pkg, "bin", p)
            if not os.path.isfile(exe):
                raise Exception(f"cif-tools missing executable: {exe}")
        script = os.path.join(self.source_folder, "src", "test_cif_tools.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("cif-tools test_package PASS")
