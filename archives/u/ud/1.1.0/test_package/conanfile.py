"""Exercise ud from the installed Conan package, not from the source tree."""

import os
import shlex

from conan import ConanFile


class UdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_ud.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(self.dependencies["ud"].package_folder, "bin", "ud")
        script = os.path.join(self.source_folder, "test_ud.py")
        self.run(f"python3 {shlex.quote(script)} {shlex.quote(binary)}",
                 cwd=self.build_folder)
