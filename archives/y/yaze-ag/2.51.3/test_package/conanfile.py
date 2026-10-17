"""Check that the packaged emulator boots on the target device."""

import os
import shlex

from conan import ConanFile


class YazeAgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_yaze.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(self.dependencies["yaze-ag"].package_folder,
                              "bin", "yaze")
        script = os.path.join(self.source_folder, "test_yaze.py")
        self.run("python3 {} {}".format(shlex.quote(script), shlex.quote(binary)),
                 cwd=self.build_folder)
