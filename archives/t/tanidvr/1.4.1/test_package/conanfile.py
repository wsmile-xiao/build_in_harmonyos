#!/usr/bin/env python3
"""Conan test_package — tanidvr 1.4.1.

Executes the packaged OHOS binaries (tanidvr / dhav2mkv) and checks their
real behaviour:

* command-line contract of both tools (help, usage errors, exit codes)
* a real conversion run: a synthetic Dahua DHAV recording stream is fed to
  ``dhav2mkv`` and the produced Matroska file is inspected byte by byte
* HarmonyOS-specific checks: aarch64 OHOS ELF, musl loader/interpreter,
  no glibc-only DT_NEEDED entries, deterministic output on OHOS

The packaged binaries are aarch64 OHOS programs, so on a cross build they are
started through qemu-aarch64 (binfmt is also usually registered).
"""

import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building

BINARIES = ("tanidvr", "dhav2mkv")


class TanidvrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _executable(self, name):
        dependency = self.dependencies["tanidvr"]
        path = os.path.join(dependency.cpp_info.bindirs[0], name)
        if not os.path.isfile(path):
            raise ConanException(f"missing packaged executable: {path}")
        return path

    def _emulator_prefixes(self, emulator):
        """Candidate qemu argument lists, most specific first."""
        sysroots = [
            os.environ.get("OHOS_SYSROOT", ""),
            os.environ.get("OHC_OHOS_SYSROOT", ""),
            "/opt/ohos-guest",
            "/opt/ohos-toolchain/sysroot",
        ]
        prefixes = [[emulator]]
        for sysroot in sysroots:
            if sysroot and os.path.isdir(sysroot):
                prefixes.append([emulator, "-L", sysroot])
        return prefixes

    def _runner(self, executable):
        if can_run(self):
            return [executable]
        if not cross_building(self):
            return [executable]
        emulator = shutil.which("qemu-aarch64")
        if not emulator:
            raise ConanException(
                "qemu-aarch64 is required to execute the OHOS aarch64 binaries"
            )
        for prefix in self._emulator_prefixes(emulator):
            try:
                self.run(shlex.join([*prefix, executable, "-h"]))
                return [*prefix, executable]
            except ConanException:
                continue
        raise ConanException(
            "qemu-aarch64 could not run the packaged OHOS binary; "
            "checked prefixes: " + ", ".join(
                " ".join(prefix) for prefix in self._emulator_prefixes(emulator)
            )
        )

    def test(self):
        tanidvr = self._runner(self._executable("tanidvr"))
        dhav2mkv = self._runner(self._executable("dhav2mkv"))
        self.run(shlex.join(tanidvr + ["-h"]))
        self.run(shlex.join(dhav2mkv + ["-h"]))
        plans = (
            ("test_tanidvr.py", ["--tanidvr", *tanidvr]),
            ("test_dhav2mkv.py", ["--dhav2mkv", *dhav2mkv, "--tanidvr", *tanidvr]),
            (
                "test_ohos_platform.py",
                ["--tanidvr", *tanidvr, "--dhav2mkv", *dhav2mkv],
            ),
        )
        for script_name, command_prefix in plans:
            script = os.path.join(self.source_folder, script_name)
            self.run(
                shlex.join([sys.executable, script, *command_prefix]),
                env="conanrun",
            )
