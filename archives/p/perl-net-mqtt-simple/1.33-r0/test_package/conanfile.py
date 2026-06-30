#!/usr/bin/env python3
"""Conan test_package — Perl module smoke test.

Verifies that Net::MQTT::Simple can be loaded via PERL5LIB.
"""
import os

from conan import ConanFile


class PerlnetmqttsimpleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Set PERL5LIB to the package's lib directory and verify module loads
        dep = self.dependencies["perl-net-mqtt-simple"]
        perl_lib = os.path.join(dep.package_folder, "lib")
        self.output.info(f"Testing with PERL5LIB={perl_lib}")
        self.run(f'PERL5LIB="{perl_lib}" perl -MNet::MQTT::Simple -e "print \'Net::MQTT::Simple loaded OK\\n\'"')
