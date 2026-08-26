#!/usr/bin/env python3
"""Consumer test for hcxtools 7.1.2 — verifies installed executables.

hcxtools is a command-line application, not a library.  The L1 test
runs the installed binary (hcxpcapngtool) to confirm the package
is functional, following the aesfix test_package pattern.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class HcxtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: packaged CLI smoke requires a runnable target")
            return

        bin_dir = os.path.join(self.dependencies["hcxtools"].package_folder, "bin")
        hcxpcapngtool = os.path.join(bin_dir, "hcxpcapngtool")

        if not os.path.isfile(hcxpcapngtool):
            raise AssertionError(f"packaged binary not found: {hcxpcapngtool}")

        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            " ".join(shlex.quote(p) for p in ["sh", script, hcxpcapngtool]),
            env="conanrun",
        )
