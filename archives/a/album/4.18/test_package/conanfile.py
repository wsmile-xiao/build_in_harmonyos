#!/usr/bin/env python3
"""test_package for album — verifies the packaged album script runs."""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class AlbumTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: package execution is skipped.")
            return
        dep = self.dependencies["album"]
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run('sh "{}" "{}"'.format(test_script, dep.package_folder), env="conanrun")
