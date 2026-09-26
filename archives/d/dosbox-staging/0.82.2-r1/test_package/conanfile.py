#!/usr/bin/env python3
"""Installed-package smoke flow for DOSBox Staging."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class DosboxStagingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "NOT_RUN DOSBOX_INSTALLED_PACKAGE_FLOW=0/1 reason=cross_building"
            )
            return
        executable = os.path.join(
            self.dependencies["dosbox-staging"].package_folder,
            "bin",
            "dosbox",
        )
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'sh "{script}" "{executable}"',
            env="conanrun",
            cwd=self.source_folder,
        )
