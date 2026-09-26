#!/usr/bin/env python3
"""test_package for shmcat 1.10 — consumer test of the installed CLI tools."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class ShmcatTestConan(ConanFile):
    """Drives the installed ``shmcat``/``ftok`` binaries through test_shmcat.sh."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _posix_shell(self):
        """R5: /system/bin/sh (mksh) cannot exec ELF binaries, so bash is needed;
        the profile's CONFIG_SHELL may point at a path that is not executable for
        this uid, hence every candidate is probed with os.access() (same rule as
        the recipe's _posix_shell)."""
        for cand in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                     "/data/service/hnp/bin/bash", "/bin/sh"):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanException("no executable shell for the consumer test")

    def test(self):
        bash = self._posix_shell()
        pkg_folder = self.dependencies["shmcat"].package_folder
        script = os.path.join(self.source_folder, "test_shmcat.sh")
        workdir = os.path.join(self.build_folder, "shmcat-tp-work")
        self.run(
            f'{bash} {script} '
            f'{os.path.join(pkg_folder, "bin", "shmcat")} '
            f'{os.path.join(pkg_folder, "bin", "ftok")} '
            f'{workdir}',
            env="conanrun",
        )
