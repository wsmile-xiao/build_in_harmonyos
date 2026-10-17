#!/usr/bin/env python3
"""test_package for openconnect 9.12 — runs the installed ``openconnect`` CLI.

The recipe installs both libopenconnect and the openconnect command-line tool;
this smoke test really executes the packaged binary and verifies the version
it reports (which also proves libopenconnect.so is loadable together with its
GnuTLS/libxml2 dependencies in the conanrun runtime environment).
"""
import os

from conan import ConanFile


class OpenconnectTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (same pattern as the repo template).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
