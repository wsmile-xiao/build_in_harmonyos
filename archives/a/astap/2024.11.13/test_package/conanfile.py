#!/usr/bin/env python3
"""Runtime tests for the packaged ASTAP command-line solver."""

import os

from conan import ConanFile


class AstapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'TEST_SOURCE_DIR="{self.source_folder}" '
            f"{bash} {self.source_folder}/test_astap.sh",
            env="conanrun",
        )
