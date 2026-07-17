#!/usr/bin/env python3
"""Conan test_package for the Homebrew flash task."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class FlashTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["flash"]
        flash = os.path.join(dep.package_folder, "bin", "flash")
        if not os.path.isfile(flash):
            raise Exception(f"Missing flash executable: {flash}")

        if not can_run(self):
            self.output.info("Cross-building; package layout check completed")
            return

        python = shutil.which("python3") or "python3"
        check_script = os.path.join(self.source_folder, "check_flash.py")
        self.run(
            f"{shlex.quote(python)} {shlex.quote(check_script)} {shlex.quote(flash)}",
            env="conanrun",
        )
        self.run(f"{shlex.quote(flash)} --version", env="conanrun")
