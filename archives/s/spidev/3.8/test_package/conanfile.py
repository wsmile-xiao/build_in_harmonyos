#!/usr/bin/env python3
"""Conan test_package for validating the spidev CPython extension."""
import glob
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SpidevTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) == "OHOS":
            self._test_ohos_extension_artifact()
            return
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_spidev.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")

    def _test_ohos_extension_artifact(self):
        package_folder = str(self.dependencies["spidev"].package_folder)
        pattern = os.path.join(
            package_folder,
            "lib",
            "python*",
            "site-packages",
            "spidev*.so",
        )
        extensions = [path for path in glob.glob(pattern) if os.path.isfile(path)]
        if len(extensions) != 1:
            raise AssertionError(
                "expected one packaged spidev extension, found {}".format(len(extensions))
            )
        test_script = os.path.join(self.source_folder, "test_spidev_static.py")
        self.run(f'"{sys.executable}" "{test_script}" "{extensions[0]}"')
