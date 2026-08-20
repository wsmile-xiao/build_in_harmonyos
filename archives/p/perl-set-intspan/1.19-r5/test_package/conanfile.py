#!/usr/bin/env python3
"""Conan test_package — Set::IntSpan Perl module.

L1 test: verify the installed Perl module can be loaded and used.
"""
import os

from conan import ConanFile


class PerlSetIntSpanTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Run the shell-wrapped Perl test script
        # PERL5LIB is set by runenv_info from the package's package_info()
        test_script = os.path.join(self.source_folder, "test_intspan.sh")
        self.run(f'sh "{test_script}"', env="conanrun")
