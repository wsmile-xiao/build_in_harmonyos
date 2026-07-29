#!/usr/bin/env python3
"""Conan test_package for gti 1.9.1.1."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class GtiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = (
            "/data/service/hnp/bin/bash"
            if str(self.settings.os) == "OHOS"
            else "/bin/sh"
        )
        if not os.path.isfile(shell):
            raise ConanException(f"Required test shell not found: {shell}")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_gti.sh")
        for case_id in ("A1", "A2", "A3", "A4", "A5"):
            command = " ".join(
                shlex.quote(part)
                for part in [shell, script, "./bin/gti", shell, case_id]
            )
            self.run(command, cwd=pkg_folder, env="conanrun")
