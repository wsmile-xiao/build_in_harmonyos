#!/usr/bin/env python3
"""Conan test_package for ausweisapp-nftrules — runs the R34 consumer check.

L1 official test: runs a Python script that verifies the packaged nftables
ruleset exists at <pkg>/etc/nftables.d/ausweisapp.nft and its content matches
the expected rule (accept tcp dport 24727). R34 real content verification.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["ausweisapp-nftrules"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_ausweisapp_nftrules.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
