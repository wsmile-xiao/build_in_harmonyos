#!/usr/bin/env python3
"""Conan consumer test for kicad-library-footprints 10.0.5."""

import os
import sys

from conan import ConanFile


class KicadLibraryFootprintsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kicad-library-footprints"].package_folder
        script = os.path.join(self.recipe_folder, "test_kicad_footprints.py")
        ohos_flag = " --ohos" if str(self.settings.os) == "OHOS" else ""
        command = '"%s" -B "%s" "%s"%s' % (
            sys.executable,
            script,
            package_folder,
            ohos_flag,
        )
        self.run(command, env="conanrun")
