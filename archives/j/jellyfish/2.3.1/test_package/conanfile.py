#!/usr/bin/env python3
"""test_package for jellyfish — consumer test of the installed CLI.

Runs test_package/test.sh, which exercises the installed `jellyfish` binary
through its real command-line interface (version, count, histo, dump, query,
info) and verifies that invalid inputs are rejected (negative controls).
"""
import os
import shutil

from conan import ConanFile


class JellyfishTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably;
        # run the consumer test with bash when available (same pattern as the
        # other CLI archives in this repository).
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        self.run(f"{shell} test.sh", env="conanrun")
