#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile


class AconfModStrongswanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["aconf-mod-strongswan"].package_folder

        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )

        script = os.path.join(
            self.source_folder,
            "test_strongswan.sh",
        )

        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )
