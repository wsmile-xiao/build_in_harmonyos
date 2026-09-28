#!/usr/bin/env python3
"""Conan consumer test for the packaged MBROLA command line synthesizer.

The real validation lives in ``test_mbrola_consumer.py``; this conanfile only
locates the packaged artifacts and drives that script through bash (the OHOS
CI runner requires a bash wrapper to execute ELF binaries).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MbrolaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Published OHOS voice database used for real end-to-end synthesis.
        self.requires("mbrola-gr2/0.0.20010521")

    def layout(self):
        basic_layout(self)

    def _bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
            "/usr/bin/bash",
            shutil.which("bash"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        if not can_run(self):
            return
        mbrola_bin = os.path.join(
            self.dependencies["mbrola"].package_folder, "bin", "mbrola"
        )
        gr2_root = self.dependencies["mbrola-gr2"].package_folder
        script = os.path.join(self.source_folder, "test_mbrola_consumer.py")
        wrapper = os.path.join(self.source_folder, "test_mbrola_consumer.sh")
        self.run(
            f'TEST_PYTHON="{sys.executable}" TEST_SCRIPT="{script}" '
            f'MBROLA_BIN="{mbrola_bin}" MBROLA_GR2_ROOT="{gr2_root}" '
            f'TEST_WORKDIR="{self.build_folder}" '
            f'"{self._bash()}" "{wrapper}"',
            env="conanrun",
        )
