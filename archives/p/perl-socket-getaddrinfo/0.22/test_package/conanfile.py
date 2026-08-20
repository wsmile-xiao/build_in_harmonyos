#!/usr/bin/env python3
"""Conan test_package — Socket::GetAddrInfo Perl XS module.

L1 test: verify the installed Perl module can be loaded and getaddrinfo works.
"""
import os

from conan import ConanFile


class PerlSocketGetaddrinfoTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Set up PERL5LIB to find the module in the Conan package
        pkg = self.dependencies["perl-socket-getaddrinfo"].package_folder
        perl_lib = os.path.join(pkg, "lib", "site_perl", "5.42.0")
        perl_arch = os.path.join(perl_lib, "aarch64-linux")

        perl5lib = f"{perl_lib}:{perl_arch}"
        os.environ["PERL5LIB"] = perl5lib
        self.run(f"sh {os.path.join(self.source_folder, 'run_test.sh')} {perl5lib}", env="conanrun")
