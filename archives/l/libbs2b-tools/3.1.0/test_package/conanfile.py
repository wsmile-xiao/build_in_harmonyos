#!/usr/bin/env python3
"""Conan test_package for libbs2b-tools 3.1.0.

The tested package ships two command line binaries, so the test runs them for
real (R34): the --version/--help exit status contract added by patch 0005, a
binaural conversion of a WAV that the test writes itself with the Python
standard library (no libsndfile on the test side), a raw PCM pipe through
bs2bstream, and a missing-input negative control.
"""
import os

from conan import ConanFile


class Libbs2bToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")