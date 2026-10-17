#!/usr/bin/env python3
"""Consumer test for the packaged bmkdep executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class BmkdepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _quote(value):
        return '"{}"'.format(str(value).replace("\\", "/").replace('"', '\\"'))

    def test(self):
        if self.settings.os not in ("Linux", "OHOS") or not can_run(self):
            self.output.info("Cross-building: runtime test is executed separately on the target")
            return

        binary = os.path.join(
            self.dependencies["bmkdep"].package_folder, "bin", "bmkdep"
        )
        if not os.path.isfile(binary):
            raise AssertionError(f"bmkdep binary not found at {binary}")

        if self.settings.os == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = str(compilers.get("c", ""))
            shell = os.path.join(os.path.dirname(cc), "bash") if cc else \
                "/data/service/hnp/bin/bash"
        else:
            shell = "bash"

        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        command = "BMKDEP={} TMPDIR={} {} test.sh".format(
            self._quote(binary), self._quote(tmp_dir), self._quote(shell)
        )
        self.run(command, env="conanrun")

        if self.settings.os == "OHOS":
            harmony_command = (
                "BMKDEP={} TMPDIR={} OHOS_TMPDIR={} "
                "/system/bin/sh test_harmonyos.sh"
            ).format(
                self._quote(binary), self._quote(tmp_dir), self._quote(tmp_dir)
            )
            self.run(harmony_command, env="conanrun")
