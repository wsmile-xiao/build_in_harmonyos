#!/usr/bin/env python3
"""Conan test_package — Net::DNS Perl module."""
import os
import glob
import tempfile

from conan import ConanFile


class PerlnetdnsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-net-dns"]
        pkg_folder = dep.package_folder
        dns_files = glob.glob(os.path.join(pkg_folder, "**", "Net", "DNS.pm"), recursive=True)
        if not dns_files:
            raise Exception("Net/DNS.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(dns_files[0]))
        # Write a simple test script to avoid shell quoting issues
        test_script = os.path.join(tempfile.gettempdir(), "test_net_dns.pl")
        with open(test_script, "w") as f:
            f.write("use Net::DNS;\n")
            f.write("print Net::DNS::version(), \"\\n\";\n")
            f.write("print \"OK\\n\";\n")
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script))
