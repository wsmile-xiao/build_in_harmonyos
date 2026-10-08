#!/usr/bin/env python3
"""Conan test_package for smem 1.5.

smem 1.5 ships two command line programs and no library API, so the consumer
is a real test driver (test_smem.py) executed with the interpreter that runs
Conan: it inspects the packaged AArch64 OHOS artifacts, then drives the
packaged `smem` script against a capture archive it synthesises in exactly the
byte layout `smemcap.c` writes, and compares every reported figure with an
independently computed expectation.

Running the packaged programs is the point of the test — none of the checks
can pass without bin/smem and bin/smemcap being present and correct.
"""
import os
import sys

from conan import ConanFile


class SmemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["smem"].package_folder, "bin")
        driver = os.path.join(self.source_folder, "test_smem.py")
        # The driver picks its own scratch directory: handing it build_folder
        # would drop the synthetic capture archive inside
        # archives/<l>/<pkg>/<ver>/test_package/, where the next `git add`
        # would pick up a stray .tar.
        self.run(f'"{sys.executable}" "{driver}" "{bindir}"')