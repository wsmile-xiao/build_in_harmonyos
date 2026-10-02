#!/usr/bin/env python3
"""Conan test_package — tgt 1.0.85.

Runs two real test scripts against the installed package (R34: the test must
drive the package's own binaries, not just print a string):

  1. test_tgt.sh            - consumer smoke: --version/--help of all three
                              programs, a tgtimg tape-image round trip, and a
                              negative check on the tgtd IPC path.
  2. ohos_specific_test.sh  - HarmonyOS consumer test derived from the upstream
                              scripts/tgt-core-test: starts tgtd on a private
                              IPC socket, creates a target, three LUNs
                              (2 disks + 1 medium changer), updates mode pages
                              and element addresses, binds an ACL, dumps
                              `tgtadm --op show`, then tears everything down.
                              34 assertions, all executed on the real platform.
"""
import os

from conan import ConanFile


class TgtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["tgt"].package_folder, "bin")
        bash = os.environ.get("CONFIG_SHELL", "bash")

        # 1) consumer smoke test
        self.run(f'{bash} "{os.path.join(self.source_folder, "test_tgt.sh")}" '
                 f'"{bindir}" "{os.path.join(self.build_folder, "consumer")}"',
                 env="conanrun")

        # 2) HarmonyOS-specific consumer test (upstream tgt-core-test port)
        work = os.path.join(self.build_folder, "ohos")
        log = os.path.join(self.build_folder, "ohos-test.log")
        self.run(f'{bash} "{os.path.join(self.source_folder, "ohos_specific_test.sh")}" '
                 f'"{bindir}" "{work}" "{log}"',
                 env="conanrun")
