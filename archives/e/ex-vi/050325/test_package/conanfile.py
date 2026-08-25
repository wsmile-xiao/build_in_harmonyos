#!/usr/bin/env python3
"""Conan test_package for ex-vi 050325 — verifies the ex binary works.

This test substantively exercises the packaged `ex` binary (R34): it runs the
editor against a real input file and asserts that ex prints the buffer and
exits cleanly. It uses the VirtualRunEnv generator so the package's bin/ is
on PATH (no need to locate the binary path manually — robust across Conan 2).
"""
import os

from conan import ConanFile


class ExViTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # use bash (provided by the conanbuild/conanrun env via CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh drives `ex` end-to-end (R34) and asserts on its output.
        self.run(f"{bash} test.sh", env="conanrun")
