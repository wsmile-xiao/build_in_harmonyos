#!/usr/bin/env python3
"""Conan test_package for abc 0.0.0.20260511.

L1 test: verify the abc binary can run the "version" command. abc is a
CLI tool (not a library), so test.c uses only standard C and invokes the
abc binary via popen(). No -I/-L/-l flags from cpp_info are needed.
"""
import os

from conan import ConanFile


class AbcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_abc")

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
        self.run(f"{bash} -c './test_abc'", env="conanrun")
