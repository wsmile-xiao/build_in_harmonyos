#!/usr/bin/env python3
"""test_package for fftresampler executable — runs test.sh which invokes the binary.

Consumer verification: generates a small PCM WAV input, runs the installed
`FFTResampler` CLI (input.wav output.wav rate) the way a real user would, and
checks exit code + output WAV header (RIFF/fmt/rate).
"""
import os

from conan import ConanFile


class FftresamplerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")