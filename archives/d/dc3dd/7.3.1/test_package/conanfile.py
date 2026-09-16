#!/usr/bin/env python3
"""Consumer-side validation for dc3dd 7.3.1."""

import os
import shutil

from conan import ConanFile


class Dc3ddTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f'"{bash}" test.sh', env="conanrun")
