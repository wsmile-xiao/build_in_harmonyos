#!/usr/bin/env python3
"""test_package for the catcodec CLI (executable package).

Runs test.sh which drives the installed catcodec binary end to end.
Suite: 11 test cases / 28 assertions:
  - 5 upstream-behaviour cases reproduced programmatically (16 assertions):
    help/version, 8-bit WAV -> .cat encode, .cat -> WAV byte-equal decode,
    16-bit roundtrip, two-sample catalogue .sfo regeneration.
  - 6 new error-path/boundary cases (12 assertions): wrong .cat extension,
    missing input file, truncated .cat, corrupt .cat header, unsupported WAV
    sample rate, malformed .sfo line.
Upstream ships no test suite; counts are synced in conanfile.py docstring,
test.sh header, MANIFEST.yml and the PR description.
"""
import os

from conan import ConanFile


class CatcodecTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) mishandles printf \x escapes and cannot
        # exec ELF binaries reliably; drive everything through the HNP bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
