#!/usr/bin/env python3
"""Conan consumer test for the chrpath command-line tool."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class ChrpathTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = "rpath_probe.c", "test.sh", "test_ohos.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler_executable(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return str(executables.get("c") or "cc")

    @staticmethod
    def _quote(value):
        if os.name == "nt":
            return str(value)
        return shlex.quote(str(value))

    def _ohos_target_args(self):
        if str(self.settings.os) != "OHOS":
            return []
        args = ["--target=aarch64-linux-ohos"]
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if sysroot:
            args.append("--sysroot=" + str(sysroot))
        return args

    def build(self):
        compiler = self._quote(self._compiler_executable())
        target_args = " ".join(
            self._quote(arg) for arg in self._ohos_target_args()
        )
        probe = self._quote(os.path.join(self.build_folder, "chrpath_rpath_probe"))
        source = self._quote(os.path.join(self.source_folder, "rpath_probe.c"))
        self.run(
            f"{compiler} {target_args} -Wl,-rpath,/data/local/tmp/chrpath-ohos-old "
            f"-o {probe} {source}",
            cwd=self.source_folder,
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip chrpath consumer execution")
            return

        shell = os.environ.get("CONFIG_SHELL") or "bash"
        if str(self.settings.os) == "OHOS":
            self.run(f'"{shell}" test_ohos.sh', env="conanrun")

        # test.sh deliberately deletes the probe's RPATH, so the target-only
        # RPATH assertion must run before the general destructive consumer
        # checks when both use the same locally-built probe.
        self.run(f'"{shell}" test.sh', env="conanrun")
