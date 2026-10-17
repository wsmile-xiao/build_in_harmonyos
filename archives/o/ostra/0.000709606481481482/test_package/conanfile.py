#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class OstraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building; layout check only")
            return

        shell = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
            or shutil.which("sh")
            or "/bin/sh"
        )
        self.run(f'"{shell}" test.sh', env="conanrun")
