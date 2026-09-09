#!/usr/bin/env python3
"""Conan test_package — bsd-games 3.3.

bsd-games is an application package (18 CLI games), so the test runs the
installed game binaries directly and asserts their observable behaviour.
The 21 assertions live in test.sh (L0c requires an independent test
source file), which this recipe invokes with the package bindir:

1. all 18 game binaries are present and executable
2. caesar without args uses frequency analysis (`find_best_rotation`,
   selects rotation 23 for "Hello World") on stdin
3. caesar with explicit shift 13
4. wump -h prints usage text
"""

from conan import ConanFile
from conan.tools.build import can_run


class BsdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["bsd-games"]
        bindir = dep.cpp_info.bindirs[0]
        self.run(f'bash test.sh "{bindir}"', env="conanrun")