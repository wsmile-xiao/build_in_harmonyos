"""Exercise the installed WCD command and shell integration."""

import os
import shlex

from conan import ConanFile


class WcdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_runtime.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["wcd"].package_folder
        script = shlex.quote(os.path.join(self.source_folder, "test_runtime.py"))
        self.run(f"python3 {script} {shlex.quote(package)}", cwd=self.build_folder)
