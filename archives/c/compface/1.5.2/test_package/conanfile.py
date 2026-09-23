#!/usr/bin/env python3
"""Conan test_package for compface 1.5.2.

compface/uncompface convert 48x48x1 images between the raw hex format
(48 lines of "0x%04X,0x%04X,0x%04X,") and the compressed printable X-Face
format. Upstream ships no automated test suite, so this consumer test
verifies real roundtrip behavior on the target:

1. compface compresses the fixed upstream-format fixture (res/test.dat)
   into a printable X-Face file (structural format check).
2. uncompface decompresses it back; the result is byte-identical to the
   fixture (lossless inverse, as documented in compface(1)).
3. uncompface -X renders the X-Face as an XBM bitmap (48 hex lines).
4. Compressing the decompressed data again reproduces the same X-Face
   (deterministic output).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CompfaceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds compface's bin dir to PATH.
            res_dir = os.path.join(self.source_folder, "res")
            self.run(
                f'sh "{os.path.join(self.source_folder, "test_compface.sh")}" '
                f'"{res_dir}"',
                env="conanrun",
            )
