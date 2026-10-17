#!/usr/bin/env python3
"""Conan test_package — lv 4.51-10.1.

Runs test.sh (bash) which sets LD_LIBRARY_PATH to the OHOS SDK system
ncurses/tinfo directory before invoking lv (binary dynamically links
libncurses.so.6 which is not on the default loader path).
"""
import os

from conan import ConanFile


class LvTestConan(ConanFile):
    """test_package for lv executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution; test.sh sets LD_LIBRARY_PATH
        # to the system ncurses/tinfo dir (libncurses.so.6 not on default path).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
