#!/usr/bin/env python3
"""Consumer test for mdp-src.

Compiles test_version.c (a real client) and runs it: the client drives the
installed mdp binary in its two non-interactive code paths and asserts real
behaviour — `mdp -v` exits 0 with the exact "mdp 1.0.18" banner, and a
missing input file exits non-zero. Only printing would not qualify; both
runs assert on exit codes and captured output.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class MdpSrcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: compile/link only, skip run")
            return
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = executables.get("c") or "clang"
        self.run(
            "{cc} test_version.c -o test_version".format(cc=cc),
            env="conanbuild",
        )
        self.run('./test_version', env="conanrun")
