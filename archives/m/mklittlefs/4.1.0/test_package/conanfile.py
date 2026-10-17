#!/usr/bin/env python3
"""Conan test_package for mklittlefs 4.1.0.

Runs test.sh which exercises create/list/unpack round-trips with the
real mklittlefs binary on programmatically generated fixtures.
"""
import os

from conan import ConanFile


class MklittlefsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"bash {script}", env="conanrun")
        # OHOS-specific: ELF properties + HMDFS create/list/extract
        ohos = os.path.join(self.recipe_folder, "test_ohos.sh")
        self.run(f"bash {ohos}", env="conanrun")
