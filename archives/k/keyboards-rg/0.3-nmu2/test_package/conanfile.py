#!/usr/bin/env python3
"""Conan consumer test for the installed keyboards-rg data package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class KeyboardsRgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_keyboards_rg.py", "test_keyboards_rg.sh", "source_inventory.json"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        if os.name != "nt":
            VirtualRunEnv(self).generate()

    def test(self):
        package = self.dependencies[self.tested_reference_str]
        export_sources = Path(self.export_sources_folder)
        inventory = export_sources / "source_inventory.json"
        if str(self.settings.os) == "OHOS" and os.name != "nt":
            script = export_sources / "test_keyboards_rg.sh"
            command = f'sh "{script}" "{package.package_folder}" "{inventory}"'
            self.run(command, env="conanrun")
        else:
            script = export_sources / "test_keyboards_rg.py"
            command = (
                f'{sys.executable} "{script}" "{package.package_folder}" '
                f'"{inventory}" "{self.settings.os}"'
            )
            if os.name == "nt":
                self.run(command)
            else:
                self.run(command, env="conanrun")
