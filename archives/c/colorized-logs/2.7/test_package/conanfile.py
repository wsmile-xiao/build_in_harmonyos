#!/usr/bin/env python3
"""test_package for colorized-logs 2.7 — runs the installed CLI tools.

Consumer verification: invoke installed ansi2html/ansi2txt/ttyrec2ansi/pipetty
the way a real user would (decode ANSI-colored log text), and check observable
output + exit codes.
"""
import os

from conan import ConanFile


class ColorizedLogsTestConan(ConanFile):
    """test_package for colorized-logs executables — runs test.sh which invokes the installed binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
