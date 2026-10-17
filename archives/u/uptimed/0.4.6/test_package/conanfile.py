#!/usr/bin/env python3
"""Consumer test for uptimed 0.4.6.

R34: executes the packaged bin/uptimed and bin/uprecords binaries via the
compiled test_uptimed harness. The harness emits HMBS hard-gate markers.

No CMakeToolchain: CMake 4.4 has no Platform/HarmonyOS module so even the
trivial test_package project() fails compiler identification
(dhcpoptinj/0.5.3 precedent). Compile the single test.c directly with
PATH clang.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UptimedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_uptimed")
        self.run(f'clang "{src}" -o "{out}"')

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_uptimed")
            self.run(f'"{test_bin}"', env="conanrun")
