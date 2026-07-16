#!/usr/bin/env python3
"""Conan test_package for enscript 1.6.6.

enscript is a CLI tool (not a library), so we exercise the installed binary
via test_enscript.sh: convert a text file to PostScript and assert the output
is a valid PostScript document.
"""
import os
import shutil

from conan import ConanFile


class EnscriptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R5: OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["enscript"].package_folder
        enscript_bin = os.path.join(pkg_folder, "bin", "enscript")
        script = os.path.join(self.source_folder, "test_enscript.sh")
        self.run(f'{bash} {script} {enscript_bin}', env="conanrun")
