#!/usr/bin/env python3
"""Conan test_package - utftex 1.31."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class UtftexTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["utftex"]
        utftex = os.path.join(dep.package_folder, "bin", "utftex")
        if not can_run(self):
            if not os.path.isfile(utftex):
                raise Exception(f"Missing packaged binary: {utftex}")
            self.output.info("Cross-building; file layout check completed")
            return

        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
        if not bash:
            raise Exception("bash not found in PATH and CONFIG_SHELL is not set; cannot run test script")
        script = os.path.join(self.source_folder, "check_utftex.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(utftex)}", env="conanrun")
