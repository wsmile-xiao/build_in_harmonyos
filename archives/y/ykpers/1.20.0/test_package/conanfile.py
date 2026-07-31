#!/usr/bin/env python3
"""test_package for ykpers/1.20.0.

Per R34, the test must substantively depend on the tested package by executing
its binary. We run ykpersonalize -V, ykinfo -V and ykchalresp -V via test.sh;
all three binaries are produced by the ykpers package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class YkpersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if self.source_folder != self.build_folder:
            copy(self, "test.sh", src=self.source_folder, dst=self.build_folder)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["ykpers"].package_folder, "bin"
        )
        test_script = os.path.join(self.build_folder, "test.sh")
        cmd = f'export PATH="{bin_dir}:$PATH" && bash "{test_script}"'
        self.run(cmd, env="conanrun", cwd=self.build_folder)
