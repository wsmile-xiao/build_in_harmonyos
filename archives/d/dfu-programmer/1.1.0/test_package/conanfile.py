#!/usr/bin/env python3
"""Conan test_package - dfu-programmer 1.1.0."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class DfuProgrammerTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["dfu-programmer"]
        dfu = os.path.join(dep.package_folder, "bin", "dfu-programmer")
        if not can_run(self):
            if not os.path.isfile(dfu):
                raise Exception(f"Missing packaged binary: {dfu}")
            self.output.info("Cross-building; file layout check completed")
            return

        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
        if not bash:
            raise Exception("bash not found in PATH and CONFIG_SHELL is not set; cannot run test script")
        script = os.path.join(self.source_folder, "check_dfu_programmer.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(dfu)}", env="conanrun")
