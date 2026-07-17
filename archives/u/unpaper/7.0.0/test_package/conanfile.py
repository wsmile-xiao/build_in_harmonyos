#!/usr/bin/env python3
"""Conan test_package for unpaper 7.0.0 — L1 consumer test.

test() invokes test.sh (under the conanrun env, whose PATH includes the
installed bin/), which runs the unpaper binary: `unpaper --version` plus a
real PPM image round-trip that exercises the libavformat/libavcodec image
I/O path at runtime (R34).
"""
import os

from conan import ConanFile


class UnpaperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
