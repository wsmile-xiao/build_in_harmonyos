#!/usr/bin/env python3
"""test_package for martin 1.13.0 — run test_martin.py against packaged bins."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MartinTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        bindir = os.path.join(self.dependencies["martin"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_martin.py")
        python = os.environ.get("PYTHON") or "python3"
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly in
        # some sandbox layouts; run through the profile's bash. `bash -c` is
        # required — passing python3 as an argument would treat it as a script.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} -c \"{python} '{script}' '{bindir}'\"", env="conanrun")
