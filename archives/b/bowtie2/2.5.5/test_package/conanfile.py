#!/usr/bin/env python3
"""Conan test_package for bowtie2 2.5.5.

bowtie2 is a CLI toolset (not a library), so the test drives the installed
ELF binaries directly: it checks `bowtie2-align-s --version`,
`bowtie2-build-s --version` and `bowtie2-inspect-s --version` all report
version 2.5.5.  The wrapper scripts (bowtie2 / bowtie2-build /
bowtie2-inspect) require Perl / Python3 which may not be present in the
OHOS CI environment, so the test invokes the native ELF binaries instead.
"""
import os
import shutil

from conan import ConanFile


class Bowtie2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_bowtie2.sh")
        self.run(f"{bash} {script}", env="conanrun")
