#!/usr/bin/env python3
"""Conan test_package for perl-net-dns-sec — Perl L1 test.

Tests that the installed Net::DNS::SEC module files exist in the package.
Note: XS .so may fail to load due to SELinux/HMDFS restrictions,
but the pure Perl fallback should still work.
"""
import os

from conan import ConanFile


class PerlnetdnssecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Check that the package contains the expected files
        pkg = self.dependencies["perl-net-dns-sec"]
        pkg_folder = pkg.package_folder

        # Module installed to system Perl site_perl arch path
        site_arch = os.path.join(pkg_folder,
                                 "data", "service", "hnp", "perl.org",
                                 "perl_5.42.0", "lib", "site_perl", "5.42.0",
                                 "aarch64-linux")

        expected_files = [
            os.path.join(site_arch, "Net", "DNS", "SEC.pm"),
            os.path.join(site_arch, "auto", "Net", "DNS", "SEC", "SEC.so"),
        ]

        for f in expected_files:
            assert os.path.isfile(f), f"Expected file not found: {f}"
            self.output.info(f"Found: {f}")

        # Try loading the module with PERL5LIB set to package path
        # Also include user's local site_perl for Net::DNS dependency
        user_site = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"
        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = f"{site_arch}:{user_site}"
        try:
            self.run(
                'perl -e "use Net::DNS::SEC; print qq(version: $Net::DNS::SEC::VERSION\\n)"'
            )
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
