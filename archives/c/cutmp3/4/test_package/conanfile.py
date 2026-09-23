#!/usr/bin/env python3
"""Functional and HarmonyOS-specific tests for packaged cutmp3."""

import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building


class Cutmp3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _runner(self, executable):
        if can_run(self):
            return [executable]
        if cross_building(self) and str(self.settings.os) == "OHOS":
            emulator = shutil.which("qemu-aarch64")
            if not emulator:
                raise ConanException(
                    "qemu-aarch64 is required for OHOS cross-validation"
                )
            return [emulator, executable]
        raise ConanException("the packaged executable cannot run in this profile")

    def test(self):
        executable = os.path.join(
            self.dependencies["cutmp3"].cpp_info.bindirs[0], "cutmp3"
        )
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")

        runner = self._runner(executable)
        for script_name in ("test_cutmp3.py", "test_ohos_tmpdir.py"):
            script = os.path.join(self.source_folder, script_name)
            command = [sys.executable, script, *runner]
            self.run(shlex.join(command), env="conanrun")
