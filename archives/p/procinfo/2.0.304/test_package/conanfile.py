#!/usr/bin/env python3
"""test_package for procinfo 2.0.304 — runs the installed `procinfo` binary.

Consumer verification: invoke the installed binary the way a real user
would, in the non-fullscreen (no curses) modes that work without a tty:
`-v`, `-h`, and the default one-shot report (interval==0 prints one report
and exits). Fullscreen mode needs a terminal and is not exercised here.
"""
import os

from conan import ConanFile


class ProcinfoTestConan(ConanFile):
    """test_package for procinfo executable — runs test.sh via bash."""
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
