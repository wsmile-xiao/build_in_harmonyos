#!/usr/bin/env python3
"""Consumer test package for abootimg."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AbootimgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["abootimg"].cpp_info.bindirs[0], "abootimg"
        )
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")
        if not can_run(self):
            self.output.info("cross build: executable exists; runtime is validated on the OHOS emulator")
            return
        script = os.path.join(self.source_folder, "test_abootimg.py")
        self.run(f'"{sys.executable}" "{script}" "{executable}"', env="conanrun")
