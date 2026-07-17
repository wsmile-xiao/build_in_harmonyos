#!/usr/bin/env python3
"""Conan test_package for md5deep 4.4.

md5deep is a CLI tool family (not a library), so the test drives the installed
binaries: it hashes a file with known content and checks md5deep / sha1deep /
sha256deep / hashdeep each report the correct digest.
"""
import os
import shutil

from conan import ConanFile


class Md5deepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        bindir = os.path.join(
            self.dependencies["md5deep"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_md5deep.sh")
        self.run(f'{bash} {script} {bindir}', env="conanrun")
