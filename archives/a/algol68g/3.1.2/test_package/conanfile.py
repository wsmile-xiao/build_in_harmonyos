#!/usr/bin/env python3
"""Conan test_package for algol68g 3.1.2.

L1 test: verify the a68g binary can compile-interpret a minimal Algol 68
program. algol68g is a CLI tool (not a library), so test.c uses only
standard C and invokes the a68g binary via popen(). No -I/-L/-l flags
from cpp_info are needed (they'd reference dirs that don't exist for a
tool package and break under strict compilers).
"""
import os

from conan import ConanFile


class Algol68GTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_algol68g")

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
        self.run(f"{bash} -c './test_algol68g'", env="conanrun")
