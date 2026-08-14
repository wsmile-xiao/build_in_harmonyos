#!/usr/bin/env python3
"""Conan test_package — perl-ole-storage_lite L1 test.

Verifies that OLE::Storage_Lite Perl module can be loaded and reports version.
"""
import os

from conan import ConanFile


class PerlolestorageliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L1: verify Perl module loads and prints version via test script
        test_script = os.path.join(self.source_folder, "test_ole_storage_lite.sh")
        self.run(f"sh {test_script}", env="conanrun")
