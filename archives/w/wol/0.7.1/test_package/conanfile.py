"""Validate installed WOL network behavior using only the local loopback."""

import os
import shlex

from conan import ConanFile


class WolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_packet.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["wol"].package_folder
        script = shlex.quote(os.path.join(self.source_folder, "test_packet.py"))
        binary = shlex.quote(os.path.join(package, "bin", "wol"))
        self.run(f"python3 {script} {binary}", cwd=self.build_folder)
