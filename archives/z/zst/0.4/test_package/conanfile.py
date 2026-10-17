#!/usr/bin/env python3
"""Conan test_package — zst/0.4 consumer test (R34).

zst is a command-line tool, so the L1 test drives the *packaged* binary
through real compress→decompress round-trips for all four supported formats
(zstd/xz/gzip/bzip2) and asserts byte-identical recovery — no library API
exists to link against.
"""
import os

from conan import ConanFile


class ZstTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries reliably —
        # wrap the driver script with bash (same as other CLI packages).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test.sh".format(bash), env="conanrun")
