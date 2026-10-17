#!/usr/bin/env python3
"""Conan test_package for libfreeaptx-tools 0.2.2.

The tested package ships two command line binaries, so the test runs them for
real (R34): the --version/--help exit status contract added by patch 0002, a
full aptX and aptX HD encode/decode round trip over a 24 bit stereo stream the
test generates itself with the Python standard library, plus negative
controls.  The byte counts asserted below are the documented aptX framing:
4 raw samples (24 bytes) become 4 bytes of aptX or 6 bytes of aptX HD, and
aptx_encode_finish() pads the 90 sample codec latency rounded up to 92
samples (23 blocks) at the end of the stream.
"""
import os

from conan import ConanFile


class LibfreeaptxToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")