#!/usr/bin/env python3

import os

from conan import ConanFile


class Ical2htmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ical2html"].package_folder

        executable = os.path.join(
            package_folder,
            "bin",
            "ical2html"
        )

        script = os.path.join(
            self.source_folder,
            "test_ical2html.py"
        )

        sample = os.path.join(
            self.source_folder,
            "sample.ics"
        )

        self.run(
            f'python3 "{script}" "{executable}" "{sample}"',
            env="conanrun"
        )
