#!/usr/bin/env python3
"""Conan consumer test for installed xkeyboard-config data."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from pathlib import Path


class XKeyboardConfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_xkeyboard_config.py", "source_inventory.json"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.info("XKEYBOARD_CONFIG_CONSUMER=NOT_RUN cross target requires W3")
            return
        package = self.dependencies[self.tested_reference_str]
        export_sources = Path(self.export_sources_folder)
        script = export_sources / "test_xkeyboard_config.py"
        inventory = export_sources / "source_inventory.json"
        self.run(
            f'python3 "{script}" "{package.package_folder}" "{inventory}"',
            env="conanrun",
        )
