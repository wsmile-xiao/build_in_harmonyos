#!/usr/bin/env python3
"""test_package for asahi-audio — verifies DSP configuration data files are installed."""

import os

from conan import ConanFile


class AsahiAudioTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["asahi-audio"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh {pkg.package_folder}", env="conanrun")
