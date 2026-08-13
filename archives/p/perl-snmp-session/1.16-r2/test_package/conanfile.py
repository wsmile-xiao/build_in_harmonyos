#!/usr/bin/env python3
"""Conan test_package — SNMP::Session Perl module.

L1 test: verify the installed Perl module can be loaded and used.
"""
import os

from conan import ConanFile


class PerlSnmpSessionTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Run the Perl test script that loads modules and tests BER encoding
        test_script = os.path.join(self.source_folder, "test_snmp_session.pl")
        self.run(f"perl {test_script}", env="conanrun")
