#!/usr/bin/env python3
"""Conan test_package for lsyncd 2.3.1 — executable smoke test.

Runs lsyncd --version to verify the binary is functional.
Uses VirtualRunEnv to set up PATH with the installed bin/ directory.
"""
import os
import shutil

from conan import ConanFile


class LsyncdTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes lsyncd."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        # Use bash to wrap binary execution.
        # R33: prefer CONFIG_SHELL env var, then shutil.which("bash"),
        # finally fall back to OHOS SDK path then "bash".
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")
