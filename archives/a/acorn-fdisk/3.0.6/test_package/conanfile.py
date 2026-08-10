#!/usr/bin/env python3
"""Consumer test package for acorn-fdisk 3.0.6."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AcornFdiskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["acorn-fdisk"].cpp_info.bindirs[0], "acorn-fdisk"
        )
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")
        if not can_run(self):
            self.output.info(
                "cross build: executable exists; runtime is validated on the OHOS device"
            )
            return
        script = os.path.join(self.source_folder, "test_acorn_fdisk.py")
        self.run(f'"{sys.executable}" "{script}" "{executable}"', env="conanrun")
