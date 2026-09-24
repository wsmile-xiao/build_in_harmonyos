#!/usr/bin/env python3
"""Conan test_package for sigar 1.6.4 — installed-package consumer verification.

Builds and runs a consumer program (test_sigar.c) that links against the
*packaged* sigar headers + library and issues real sigar C API calls to read
live OS/hardware metrics on the HarmonyOS/Linux device (memory, CPU, swap,
uptime, load average, pid, file systems, sys info, version).

The 13 OFFICIAL upstream test programs (tests/t_sigar_*.c) are built and run
separately by the main recipe's build() step as `make check`; this program is
the installed-package contract check.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("test_sigar",)


class SigarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("sigar consumer binary cannot run on this platform")
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            result = self.run(f'"{executable}"', env="conanrun", ignore_errors=True)
            marker = {
                "executed": True,
                "passed": result == 0,
                "command": executable,
                "discovered": 1,
                "passedCount": 1 if result == 0 else 0,
            }
            print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(marker, separators=(",", ":")))
            if result != 0:
                raise ConanException("test_sigar consumer check failed (exit %s)" % result)
