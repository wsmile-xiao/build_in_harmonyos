#!/usr/bin/env python3
"""Conan test_package — perl-spiffy 0.46

Tests that Spiffy can be loaded and its core features (field, const,
mixin, super, stub/export) work correctly on OpenHarmony.
"""
import os

from conan import ConanFile


class PerlSpiffyTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Spiffy.pm in the package folder
        pkg = self.dependencies["perl-spiffy"]
        pkg_folder = pkg.package_folder

        # Spiffy.pm is at lib/perl5/Spiffy.pm (INSTALL_BASE=/ layout)
        lib_dir = os.path.join(pkg_folder, "lib", "perl5")
        if not os.path.exists(os.path.join(lib_dir, "Spiffy.pm")):
            # Search in versioned subdirectories
            for root, _, files in os.walk(lib_dir):
                if "Spiffy.pm" in files:
                    lib_dir = root
                    break

        spiffy_pm = os.path.join(lib_dir, "Spiffy.pm")
        if not os.path.exists(spiffy_pm):
            raise Exception("Spiffy.pm not found in package")
        self.output.success(f"Found Spiffy.pm: {spiffy_pm}")

        # Verify mixin.pm exists
        mixin_pm = os.path.join(lib_dir, "Spiffy", "mixin.pm")
        if not os.path.exists(mixin_pm):
            raise Exception("Spiffy/mixin.pm not found in package")
        self.output.success(f"Found Spiffy/mixin.pm: {mixin_pm}")

        # Run the test script with PERL5LIB set to the lib directory
        self.run(f"PERL5LIB={lib_dir} sh test_spiffy.sh")
