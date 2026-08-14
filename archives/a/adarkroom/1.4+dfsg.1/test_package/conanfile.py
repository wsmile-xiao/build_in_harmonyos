#!/usr/bin/env python3
"""Conan test_package — adarkroom 1.4+dfsg.1.

Runs a real consumer test: verifies the packaged browser-game assets
(index.html, engine.js, css, audio, img, lang, licenses) are actually
installed in the package and contain real content.
"""
import os

from conan import ConanFile


class AdarkroomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["adarkroom"].package_folder
        script = os.path.join(self.source_folder, "test_adarkroom.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
