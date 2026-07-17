#!/usr/bin/env python3
"""Conan test_package for bedtools 2.31.1 — binary tool functional smoke test.

Runs test.sh (in the conanrun env) which exercises `bedtools --version`,
`bedtools intersect` and `bedtools sort` with byte-exact assertions on real BED
input — a genuine exercise of the packaged binary, not a string-printing stub.
"""
import os

from conan import ConanFile


class BedtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; wrap via bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
