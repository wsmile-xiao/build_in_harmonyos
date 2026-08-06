#!/usr/bin/env python3
"""Conan test_package for ttf-cousine 3.4.0."""

import os

from conan import ConanFile


class TtfcousineTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ttf-cousine"]
        resdirs = dep.cpp_info.resdirs or []
        if not resdirs:
            raise Exception("ttf-cousine package_info declared no resdirs")

        pkg_folder = dep.package_folder
        font_dirs = []
        for rd in resdirs:
            font_dirs.append(rd if os.path.isabs(rd) else os.path.join(pkg_folder, rd))

        test_script = os.path.join(self.source_folder, "test_fonts.py")
        args = " ".join(f'"{font_dir}"' for font_dir in font_dirs)
        self.run(f'python3 "{test_script}" {args}', env="conanrun")
