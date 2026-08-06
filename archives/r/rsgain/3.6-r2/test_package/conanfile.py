#!/usr/bin/env python3
"""Conan test_package for rsgain 3.6-r2 — L1 consumer test.

test() invokes test.sh (under the conanrun env, whose PATH includes the
installed bin/), which runs the rsgain binary: `rsgain --version` plus a
real WAV file scan that exercises the libavformat/libavcodec/libswresample
decode path and libebur128 loudness measurement at runtime (R34).
"""
import os

from conan import ConanFile


class RsgainTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} {os.path.join(self.source_folder, 'test.sh')}", env="conanrun")
