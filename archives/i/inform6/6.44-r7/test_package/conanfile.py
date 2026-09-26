#!/usr/bin/env python3
"""Consumer test for inform6/6.44-r7.

Runs the packaged compiler against two real Z-machine game sources
(minimal library entry + the upstream `advent.inf` standard demo) and
verifies the produced story files byte-wise.
"""
import os
import shutil

from conan import ConanFile


class Inform6TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        dep = self.dependencies["inform6"]
        script = os.path.join(self.source_folder, "test_inform6.sh")
        self.run(f'{bash} {script} "{dep.package_folder}" "{self.build_folder}"',
                 env="conanrun")
