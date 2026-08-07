#!/usr/bin/env python3
"""Conan test_package — cc65 2.19.

Verifies that the cc65 compiler binary is installed and functional.
Runs cc65 --version to check the binary executes, then compiles a
minimal C program to 6502 assembly (cc65 -c test.c) to verify the
compiler core works (R34: exercise the tested package's binary).

The cc65 tools run on the build host and generate 6502 target code;
they do not execute 6502 code on the host, so no target runtime is needed.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class Cc65TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # cc65 tools are aarch64 binaries; skip if cross-compiling
        # (target binary cannot run on x86_64 build host).
        if cross_building(self):
            return

        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        # Prefer CONFIG_SHELL, then search PATH, finally fall back to known path.
        import shutil
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f'"{bash}" test.sh', env="conanrun")
