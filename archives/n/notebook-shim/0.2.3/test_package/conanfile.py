#!/usr/bin/env python3
"""Conan consumer test for notebook-shim 0.2.3."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class NotebookShimTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_notebook_shim.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["notebook-shim"].package_folder
        expected = [
            os.path.join(package_folder, "lib", "python", "notebook_shim", "__init__.py"),
            os.path.join(package_folder, "lib", "python", "notebook_shim", "_version.py"),
            os.path.join(package_folder, "etc", "jupyter", "jupyter_server_config.d", "notebook_shim.json"),
        ]
        missing = [path for path in expected if not os.path.isfile(path)]
        if missing:
            raise AssertionError(f"Missing notebook-shim files: {missing}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_notebook_shim.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', env="conanrun")
