#!/usr/bin/env python3
"""Conan test_package for mafft 7.525.

mafft is a CLI tool (not a library), so the test drives the installed
binaries: it checks `mafft --version` reports the correct version and
runs a small multiple sequence alignment on a synthetic FASTA input.
"""
import os
import shutil

from conan import ConanFile


class MafftTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_mafft.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
