#!/usr/bin/env python3
"""Conan test_package for perl-libwww 6.83 — consumer check.

Runs test_libwww.py (real test source file, satisfies L0c) against the
installed site_perl: loads LWP::UserAgent and verifies version 6.x.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlLibwwwTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-libwww"].package_folder
        site = os.path.join(pkg, "lib", "perl5", "site_perl")
        test_script = os.path.join(os.path.dirname(__file__), "test_libwww.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_libwww.py missing: {test_script}")
        # LWP::UserAgent needs HTTP::Request/URI/etc. (from HTTP-Message and
        # friends) which are NOT published to ohpcd as conan packages — the
        # isolated conan perl lacks them. Use the full system perl
        # (usr/local), which has the dependency chain, plus our site_perl
        # (same pattern as unicorn's python3 pinning).
        py_perl = "/storage/Users/currentUser/usr/local/bin/perl"
        if not os.path.isfile(py_perl):
            py_perl = "perl"
        self.run(
            f'PERL_BIN="{py_perl}" '
            f'PERL5LIB_EXTRA="/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2" '
            f'python3 "{test_script}" "{site}"'
        )
