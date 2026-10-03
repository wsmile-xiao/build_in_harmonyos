"""Consumer smoke test for the packaged mdetect command."""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class MdetectTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip mdetect runtime smoke test")
            return

        package = self.dependencies["mdetect"]
        bindir = package.cpp_info.bindirs[0] if package.cpp_info.bindirs else "bin"
        executable = os.path.join(package.package_folder, bindir, "mdetect")
        runner = os.path.join(self.recipe_folder, "test.py")
        self.run(f'python3 "{runner}" "{executable}"')
