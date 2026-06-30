#!/usr/bin/env python3
"""Conan test_package for perl-protocol-irc 0.13 (Protocol::IRC).

Verifies that the Perl module can be loaded after installation.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlProtocolIRCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # No build needed for Perl module test
        pass

    def test(self):
        # Verify the Perl module can be loaded
        self.run("perl -MProtocol::IRC -e 'print \"Protocol::IRC version \", $Protocol::IRC::VERSION, \"\\n\"'", env="conanrun")
