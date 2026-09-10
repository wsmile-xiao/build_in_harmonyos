#!/usr/bin/env python3
"""test_package for fdk-aac-encoder — fdkaac CLI encoder.

R34: test generates real PCM audio, encodes it with the packaged fdkaac
binary, and inspects the resulting M4A/ADTS outputs (container boxes,
sync word, size sanity). The heavy lifting lives in test.sh so the CI
L0c "test source file" gate can see a real source file.
"""
import os

from conan import ConanFile


class FdkAacEncoderTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        fdkaac = os.path.join(
            self.dependencies["fdk-aac-encoder"].package_folder, "bin", "fdkaac"
        )
        # Upstream fdkaac prints its version banner via usage() and *by
        # design* exits with status 1 even for --help (src/main.c:
        # `case 'h': return usage(), -1;`), so test.sh checks the banner
        # text instead of the exit code.
        test_sh = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f'sh "{test_sh}" "{fdkaac}" "{self.build_folder}"', env="conanrun")
