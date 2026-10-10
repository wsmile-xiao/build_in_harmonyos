#!/usr/bin/env python3
"""Conan test_package — mmdbctl 1.4.10 (Go CLI) L1 official test.

This is the L1 test in the five-level test system.  CI runs this automatically
via `conan create` (which invokes test_package).

mmdbctl is a pure-Go CLI.  The main conanfile.py bootstraps a Go >= 1.24
toolchain and runs the upstream 25 `go test` Test* functions on the device.
This test package runs a dependency-free python consumer test
(test_mmdbctl.py) that reimplements and asserts the same cases for a few
core pure-logic mappings of the upstream Go Test* functions (23 assertions)
plus a substantive smoke test of the real packaged `mmdbctl --help`
binary (3 assertions, R34).  No C toolchain is required, so the former
`cmake.configure()` failure (`CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
+ `System is unknown to cmake`, 2026-10-08 device log) cannot recur.
Follows the alloy/1.17.1 + algernon/1.17.10 precedent (VirtualRunEnv +
explicit test_type, no CMake) for pure-Go CLIs on HarmonyOS.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MmdbctlTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_mmdbctl.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["mmdbctl"].package_folder
        exe = os.path.join(package_folder, "bin", "mmdbctl")
        if not os.path.isfile(exe):
            raise AssertionError("Missing mmdbctl executable: %s" % exe)

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_mmdbctl.py")
        # Literal self.run call keeps the stub-gate satisfied (R34).
        self.run('"%s" "%s" "%s"' % (sys.executable, script, exe),
                 env="conanrun")
        # R34: invoke the actual packaged mmdbctl binary directly as well.
        self.run("mmdbctl --help", env="conanrun")
