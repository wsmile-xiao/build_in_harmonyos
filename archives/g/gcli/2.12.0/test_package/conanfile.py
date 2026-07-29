#!/usr/bin/env python3
"""Conan test_package for the Homebrew gcli task."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class GcliTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["gcli"]
        gcli = os.path.join(dep.package_folder, "bin", "gcli")
        if not os.path.isfile(gcli):
            raise Exception(f"Missing gcli executable: {gcli}")

        if not can_run(self):
            self.output.info("Cross-building; package layout check completed")
            return

        python = shutil.which("python3") or "python3"
        check_script = os.path.join(self.source_folder, "check_gcli.py")
        self.run(
            f"{shlex.quote(python)} {shlex.quote(check_script)} {shlex.quote(gcli)}",
            env="conanrun",
        )
        self.run(f"{shlex.quote(gcli)} version", env="conanrun")
