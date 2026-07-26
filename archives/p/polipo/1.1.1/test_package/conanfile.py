#!/usr/bin/env python3
"""Conan test_package for polipo 1.1.1."""
import os
import shutil

from conan import ConanFile


class PolipoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        package_folder = self.dependencies["polipo"].package_folder
        polipo_bin = os.path.join(package_folder, "bin", "polipo")
        index_file = os.path.join(
            package_folder, "share", "polipo", "www", "index.html"
        )
        if not os.path.isfile(index_file):
            raise RuntimeError("packaged Polipo web index is missing")
        www_dir = os.path.dirname(index_file)
        script = os.path.join(self.source_folder, "test_polipo.sh")
        self.run(
            f'"{bash}" "{script}" "{polipo_bin}" "{www_dir}"', env="conanrun"
        )
