#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Guess (pure Perl module).

Verifies that the package contains the Guess.pm file and that the module
can be loaded and its exported functions work correctly.
"""
import os
import glob
import tempfile

from conan import ConanFile


class CryptOpensslGuessTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["crypt-openssl-guess"]
        pkg_folder = dep.package_folder
        guess_files = glob.glob(
            os.path.join(pkg_folder, "**", "Crypt", "OpenSSL", "Guess.pm"),
            recursive=True,
        )
        if not guess_files:
            raise Exception("Crypt/OpenSSL/Guess.pm not found in package")
        perl_lib_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(guess_files[0]))
        )

        # 1. Verify package artifact integrity via test_package.py
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run('python3 "{}" "{}"'.format(test_script, guess_files[0]))

        # 2. Functional test: load module and call all exported functions with assertions
        func_test = os.path.join(tempfile.gettempdir(), "test_crypt_openssl_guess.pl")
        with open(func_test, "w") as f:
            f.write("use strict;\n")
            f.write("use warnings;\n")
            f.write("use Crypt::OpenSSL::Guess qw(openssl_inc_paths openssl_lib_paths find_openssl_prefix openssl_version);\n")
            f.write('my $inc = openssl_inc_paths();\n')
            f.write('my $lib = openssl_lib_paths();\n')
            f.write('my $prefix = find_openssl_prefix();\n')
            f.write('my $version = openssl_version();\n')
            f.write('print "INC: $inc\\n";\n')
            f.write('print "LIB: $lib\\n";\n')
            f.write('print "PREFIX: $prefix\\n";\n')
            f.write('print "VERSION: $version\\n";\n')
            f.write('die "FAIL: openssl_lib_paths returned undef" unless defined $lib;\n')
            f.write('die "FAIL: openssl_lib_paths returned empty" unless length($lib);\n')
            f.write('die "FAIL: find_openssl_prefix returned undef" unless defined $prefix;\n')
            f.write('die "FAIL: find_openssl_prefix returned empty" unless length($prefix);\n')
            f.write('print "ALL ASSERTIONS PASSED\\n";\n')
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, func_test))
