#!/usr/bin/env python3
"""Consumer tests for x86_64-elf-grub 2.12."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class X8664ElfGrubTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("x86_64-elf-binutils/2.46.1")

    def test(self):
        grub_package = self.dependencies["x86_64-elf-grub"].package_folder
        binutils_package = self.dependencies.build[
            "x86_64-elf-binutils"
        ].package_folder
        assembler = os.path.join(
            binutils_package, "bin", "x86_64-elf-as"
        )
        shell = self._pipefail_shell()
        self.run(
            shlex.join([shell, "test.sh", grub_package, assembler]),
            env="conanrun",
        )

    def _pipefail_shell(self):
        candidates = (
            ("/system/bin/sh",)
            if str(self.settings.os) == "OHOS"
            else (os.environ.get("CONFIG_SHELL"), "bash", "zsh", "sh")
        )
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            resolved = (
                candidate
                if os.path.isabs(candidate)
                else shutil.which(candidate)
            )
            if not resolved:
                continue
            resolved = os.path.realpath(resolved)
            if resolved in seen:
                continue
            seen.add(resolved)
            if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
                continue
            try:
                probe = subprocess.run(
                    [resolved, "-c", "set -o pipefail"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=5,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if probe.returncode == 0:
                return resolved

        raise ConanInvalidConfiguration(
            "a shell with 'set -o pipefail' support is required to run "
            "the GRUB tests"
        )
