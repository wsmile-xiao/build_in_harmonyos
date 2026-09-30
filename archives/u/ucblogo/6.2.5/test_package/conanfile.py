#!/usr/bin/env python3
"""Consumer test for the installed ucblogo executable."""

import os
import shutil

from conan import ConanFile


class UCBLogoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        package_folder = self.dependencies["ucblogo"].package_folder
        binary = os.path.join(package_folder, "bin", "ucblogo")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{bash} "{script}" "{binary}"', env="conanrun")
