#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["libxkbcommon"].package_folder
        header = os.path.join(pkg, "include", "xkbcommon", "xkbcommon.h")
        found = os.path.isfile(header)
        self.output.info(f"xkbcommon.h found: {found} ({header})")
        if not found:
            raise Exception("libxkbcommon package missing")
        script = os.path.join(self.source_folder, "src", "test_libxkbcommon.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("libxkbcommon test_package PASS")
