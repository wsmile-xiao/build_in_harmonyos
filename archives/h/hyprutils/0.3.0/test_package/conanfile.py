#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["hyprutils"].package_folder
        pkg_ok = os.path.isdir(os.path.join(pkg, "include", "hyprutils"))
        self.output.info(f"hyprutils include found: {pkg_ok} ({pkg})")
        if not pkg_ok:
            raise Exception("hyprutils package missing")
        script = os.path.join(self.source_folder, "src", "test_hyprutils.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("hyprutils test_package PASS")
