#!/usr/bin/env python3
"""Conan consumer tests for the png2ico command-line application."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.errors import ConanInvalidConfiguration


class Png2icoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = (
        "png2ico_test_common.h",
        "test_png2ico.c",
        "test_ohos.c",
    )
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        temp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(temp_dir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", temp_dir)
        env.vars(self, scope="run").save_script("png2ico_test")

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return str(executables.get("c") or "cc")

    @staticmethod
    def _quote(value):
        if os.name == "nt":
            return '"' + str(value).replace('"', '\\"') + '"'
        return shlex.quote(str(value))

    def _target_flags(self):
        flags = [
            str(flag)
            for flag in self.conf.get("tools.build:cflags", default=[],
                                     check_type=list)
        ]
        if str(self.settings.os) == "OHOS":
            if not any(flag.startswith("--target=") for flag in flags):
                flags.append("--target=aarch64-linux-ohos")
            sysroot = self.conf.get("tools.build:sysroot", default=None)
            if sysroot and not any(flag.startswith("--sysroot=") for flag in flags):
                flags.append("--sysroot=" + str(sysroot))
        return flags

    def build(self):
        compiler = self._quote(self._compiler())
        include_dir = self._quote(self.source_folder)
        common = (
            f"{compiler} -std=c11 -O2 -Wall -Wextra -Werror "
            f"{' '.join(self._quote(flag) for flag in self._target_flags())} "
            f"-I{include_dir}"
        )
        test_binary = self._quote(os.path.join(self.build_folder, "test_png2ico"))
        test_source = self._quote(os.path.join(self.source_folder, "test_png2ico.c"))
        self.run(f"{common} -o {test_binary} {test_source}", cwd=self.source_folder)

        if str(self.settings.os) == "OHOS":
            ohos_binary = self._quote(os.path.join(self.build_folder, "test_ohos"))
            ohos_source = self._quote(os.path.join(self.source_folder, "test_ohos.c"))
            self.run(f"{common} -o {ohos_binary} {ohos_source}",
                     cwd=self.source_folder)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "png2ico test_package must run on a native Linux/OHOS environment"
            )

        binary = os.path.join(
            self.dependencies["png2ico"].package_folder, "bin", "png2ico"
        )
        test_binary = os.path.join(self.build_folder, "test_png2ico")
        self.run(f"{self._quote(test_binary)} {self._quote(binary)}",
                 env=["conanrun", "png2ico_test"])

        if str(self.settings.os) == "OHOS":
            ohos_binary = os.path.join(self.build_folder, "test_ohos")
            self.run(f"{self._quote(ohos_binary)} {self._quote(binary)}",
                     env=["conanrun", "png2ico_test"])
