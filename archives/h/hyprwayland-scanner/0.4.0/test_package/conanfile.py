#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["hyprwayland-scanner"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        scanner = os.path.join(bin_dir, "hyprwayland-scanner")
        found = os.path.isfile(scanner)
        self.output.info(f"hyprwayland-scanner found: {found} ({scanner})")
        if not found:
            raise Exception("hyprwayland-scanner binary missing")
        script = os.path.join(self.source_folder, "src", "test_hyprwayland-scanner.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{bin_dir}"', env="conanrun")
        self.output.info("hyprwayland-scanner test_package PASS")
