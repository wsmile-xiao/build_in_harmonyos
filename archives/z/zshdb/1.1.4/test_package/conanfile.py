"""Exercise the installed debugger, not the source tree."""

import os
import shlex

from conan import ConanFile


class ZshdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_zshdb.py", "sample.zsh", "commands.txt"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(self.dependencies["zshdb"].package_folder, "bin", "zshdb")
        script = os.path.join(self.source_folder, "test_zshdb.py")
        self.run(
            f"python3 {shlex.quote(script)} {shlex.quote(binary)} "
            f"{shlex.quote(self.source_folder)}",
            cwd=self.build_folder,
        )
