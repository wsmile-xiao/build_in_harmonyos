#!/usr/bin/env python3
"""Conan test_package for mutt 2.4.1.

R34: test_package must actually run the mutt binary, not just print a string.
Uses explicit binary path so L1e destructive test (bin/ moved away) reliably fails.
Skips can_run() because the default build profile (os=HarmonyOS) differs from
the CI host profile (os=OHOS) — same platform, different Conan setting name.
"""
import os
from conan import ConanFile


class MuttTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run the actual mutt binary via explicit path so the test
        # genuinely depends on the package artifact (L1e negative test safe)
        mutt_bin = os.path.join(
            self.dependencies["mutt"].package_folder, "bin", "mutt"
        )
        self.run(f'"{mutt_bin}" -v', env="conanrun")
