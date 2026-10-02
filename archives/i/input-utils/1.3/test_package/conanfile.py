#!/usr/bin/env python3
"""Conan test_package for input-utils 1.3.

Two real test sources are compiled and executed against the packaged ELF
tools (no print-only stub):
  - test_input_utils.c : compiled with clang in build(), run in test();
    asserts exit codes / usage rejection of lsinput, input-events,
    emulate-key and input-send.
  - test.sh            : executed with bash in test(); 5 shell assertions
    covering the same packaged binaries (conanrun env PATH via VirtualRunEnv).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class InputUtilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the C consumer test (no extra deps; system libc only).
        self.run("clang -O1 -Wall -o test_input_utils test_input_utils.c")

    def test(self):
        if not can_run(self):
            raise ConanException("input-utils tools are not runnable here")
        # 1) run the compiled C consumer test against the packaged tools
        self.run("./test_input_utils", env="conanrun")
        # 2) run the shell assertions (conanrun env puts package bindir on PATH)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
