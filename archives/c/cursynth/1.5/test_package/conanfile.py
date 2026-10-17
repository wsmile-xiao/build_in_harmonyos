#!/usr/bin/env python3
"""Conan test_package for cursynth 1.5 — L1 consumer test.

cursynth is a CLI tool (not a library): test.c runs the packaged binary and
asserts on its behaviour (version banner, and the no-audio-device path taken
by the OSS back-end on platforms without /dev/dsp).
"""
import os

from conan import ConanFile


class CursynthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_cursynth")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
        # binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        self.run(f"{bash} -c './test_cursynth'", env="conanrun")
