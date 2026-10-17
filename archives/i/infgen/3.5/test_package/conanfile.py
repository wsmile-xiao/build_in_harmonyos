#!/usr/bin/env python3
"""Functional test package for infgen 3.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS runtime has no `bash` on PATH; use the HNP bash absolute path
        # (same pattern as rgbds). can_run() is true for native device builds.
        if str(self.settings.os) == "OHOS" or can_run(self):
            shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", shell)
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'{shell} "{script}"', env="conanrun")
