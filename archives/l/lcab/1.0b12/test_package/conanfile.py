#!/usr/bin/env python3
"""Conan test_package for lcab 1.0b12.

lcab is a command-line tool, so the test drives the installed binary:
version banner, cabinet creation (single/multi file, -n/-q/-r) and
verification of the produced cabinet content.
"""
import os
import platform
import sys

from conan import ConanFile
from conan.tools.build import can_run


class LcabTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(self.dependencies["lcab"].package_folder, "bin", "lcab")
        if not os.path.isfile(binary):
            raise RuntimeError("lcab package binary is missing")
        if not can_run(self):
            return
        if str(self.settings.arch) == "armv8" and platform.machine() not in ("aarch64", "arm64"):
            self.output.info("Skipping target execution on a non-AArch64 build machine")
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries -> use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists(bash):
            bash = "bash"
        script = os.path.join(self.source_folder, "test_lcab.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
        # End-to-end consumer use case: pack a sandbox directory with lcab -r,
        # read it back with an independent MS-CAB parser, verify checksums and
        # byte-identical extraction.
        roundtrip = os.path.join(self.source_folder, "test_roundtrip.py")
        self.run(f'"{sys.executable}" "{roundtrip}" "{binary}"', env="conanrun")
