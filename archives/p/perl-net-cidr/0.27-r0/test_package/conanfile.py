#!/usr/bin/env python3
"""Conan test_package — Net::CIDR (pure Perl module)."""
import os
import glob
import tempfile

from conan import ConanFile


class PerlnetcidrTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-net-cidr"]
        pkg_folder = dep.package_folder
        cidr_files = glob.glob(os.path.join(pkg_folder, "**", "Net", "CIDR.pm"), recursive=True)
        if not cidr_files:
            raise Exception("Net/CIDR.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(cidr_files[0]))
        # Write a simple test script to avoid shell quoting issues
        test_script = os.path.join(tempfile.gettempdir(), "test_net_cidr.pl")
        with open(test_script, "w") as f:
            f.write("use Net::CIDR;\n")
            f.write("my @r = Net::CIDR::range2cidr(\"192.168.1.1-192.168.1.5\");\n")
            f.write("print scalar(@r) . \" CIDR blocks\\n\";\n")
            f.write("print \"OK\\n\" if @r;\n")
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script))
