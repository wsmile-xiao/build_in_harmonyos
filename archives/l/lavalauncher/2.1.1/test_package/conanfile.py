#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lavalauncher"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        launcher = os.path.join(bin_dir, "lavalauncher")
        found = os.path.isfile(launcher)
        self.output.info(f"lavalauncher found: {found} ({launcher})")
        if not found:
            raise Exception("lavalauncher binary missing")
        script = os.path.join(self.source_folder, "src", "test_lavalauncher.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{bin_dir}"', env="conanrun")
        self.output.info("lavalauncher test_package PASS")
