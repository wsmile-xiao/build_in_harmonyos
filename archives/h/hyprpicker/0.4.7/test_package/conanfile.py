#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["hyprpicker"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        picker = os.path.join(bin_dir, "hyprpicker")
        found = os.path.isfile(picker)
        self.output.info(f"hyprpicker found: {found} ({picker})")
        if not found:
            raise Exception("hyprpicker binary missing")
        script = os.path.join(self.source_folder, "src", "test_hyprpicker.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{bin_dir}"', env="conanrun")
        self.output.info("hyprpicker test_package PASS")
