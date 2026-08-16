#!/usr/bin/env python3
"""Functional package test for cmus 2.12.0."""
import os

from conan import ConanFile


class CmusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["cmus"].package_folder
        cmus = os.path.join(package, "bin", "cmus")
        remote = os.path.join(package, "bin", "cmus-remote")
        script = os.path.join(self.source_folder, "test_cmus.sh")
        shell = (
            "/data/service/hnp/bin/bash"
            if self.settings.os == "OHOS"
            else "/bin/bash"
        )
        self.run(
            f'"{shell}" "{script}" "{cmus}" "{remote}" "{package}"',
            env="conanrun",
        )
