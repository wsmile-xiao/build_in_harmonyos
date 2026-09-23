#!/usr/bin/env python3
"""Consumer test for dhcpoptinj 0.5.3.

R34: executes the packaged sbin/dhcpoptinj binary via the compiled
test_dhcpoptinj harness. The harness emits HMBS hard-gate markers.

No CMakeToolchain: CMake 4.4 has no Platform/HarmonyOS module so even the
trivial test_package project() fails compiler identification (preflight
2026-09-12: test package CMake Error at CMakeLists.txt:2). Compile the
single test.c directly with PATH clang (bvi/1.5.0 precedent).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DhcpoptinjTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_dhcpoptinj")
        self.run(f'clang "{src}" -o "{out}"')

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_dhcpoptinj")
            self.run(f'"{test_bin}"', env="conanrun")
