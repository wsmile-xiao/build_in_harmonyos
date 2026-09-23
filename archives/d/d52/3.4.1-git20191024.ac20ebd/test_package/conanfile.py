#!/usr/bin/env python3
"""Conan test_package for d52 — runs the installed disassemblers and asserts real output.

The test itself is test_package/test.sh (POSIX sh): it executes the three
installed executables from bin/ and compares their disassembly output with the
expected output files that upstream ships in its own cyclefiles/ directory
(upstream has no test target of its own — see MANIFEST.yml).
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class D52TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keeps build/test artifacts out of the package source directory.
        basic_layout(self)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        data_dir = os.path.join(self.source_folder, "data")
        self.run(
            f'/bin/sh "{script}" "{data_dir}" "{self.build_folder}"',
            env="conanrun",
        )
