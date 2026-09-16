#!/usr/bin/env python3
"""Conan consumer test for zenlisp 2013.11.22."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ZenlispTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["zenlisp"]
        zl = os.path.join(dep.package_folder, "bin", "zl")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            '"{}" test_zenlisp.sh "{}"'.format(bash, zl),
            env="conanrun",
        )
