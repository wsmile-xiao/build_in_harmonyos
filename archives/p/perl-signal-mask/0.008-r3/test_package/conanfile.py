#!/usr/bin/env python3
"""Conan test_package — perl-signal-mask 0.008-r3

Tests that Signal::Mask and Signal::Pending can be loaded
and basic signal mask operations work correctly.
IPC::Signal is bundled in the package (lib/perl5/IPC/Signal.pm).
Uses test_signal_mask.sh which exercises the module's API.
"""
import os
import glob

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlSignalMaskTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies["perl-signal-mask"]
        pkg_folder = pkg.package_folder

        # lib_dir contains Signal/Mask.pm and IPC/Signal.pm
        lib_dir = os.path.join(pkg_folder, "lib", "perl5")

        test_script = os.path.join(self.source_folder, "test_signal_mask.sh")
        self.run(f'PERL5LIB={lib_dir} sh {test_script}', env="conanrun")
