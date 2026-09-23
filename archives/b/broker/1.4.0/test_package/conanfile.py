#!/usr/bin/env python3
"""Consumer tests for broker/1.4.0 (test_package).

Verifies that an external consumer can link against the installed libbroker
(plus the bundled CAF static libraries and headers) and exercise the broker
public API end to end on HarmonyOS PC.

7 consumer cases (30 assertions) run through CTest; see MANIFEST.yml.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BrokerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # Run every registered consumer case (single binary, one subcommand
        # per case) and fail on the first non-zero result. The binary is
        # linked into the CMake build root (no RUNTIME_OUTPUT_DIRECTORY).
        exe = os.path.join(self.build_folder, "test_broker")
        if not os.path.isfile(exe):
            exe = os.path.join(self.cpp.build.bindirs[0], "test_broker")
        for case in ("version", "roundtrip", "filter", "burst", "store",
                     "peer_error", "status"):
            self.run('"%s" %s' % (exe, case), env="conanrun")
