#!/usr/bin/env python3
"""Consumer test package for ACR."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AcrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["acr"].cpp_info.bindirs
        executable = os.path.join(bindirs[0], "acr")
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")
        if not can_run(self):
            self.output.info("cross build: packaged scripts exist; runtime is validated on the OHOS emulator")
            return
        test_script = os.path.join(self.source_folder, "test_acr.py")
        self.run(f'"{sys.executable}" "{test_script}" "{executable}"', env="conanrun")
