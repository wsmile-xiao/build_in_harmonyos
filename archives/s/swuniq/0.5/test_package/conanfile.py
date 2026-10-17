#!/usr/bin/env python3
"""Conan consumer — exercise the packaged swuniq CLI on OHOS aarch64."""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
import os
import platform
import shlex
import shutil


class SwuniqTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        args = [cc, "-O2", "-static", os.path.join(self.source_folder, "test.c"),
                "-o", os.path.join(self.build_folder, "test_swuniq")]
        self.run(" ".join(shlex.quote(str(arg)) for arg in args))

    def test(self):
        exe = os.path.join(self.build_folder, "test_swuniq")
        tool = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                            "bin", "swuniq")
        command = [exe, tool]
        if platform.machine().lower() not in ("aarch64", "arm64"):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration("aarch64 runner or qemu-aarch64 required")
            command = [qemu, exe, tool, qemu]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
