#!/usr/bin/env python3
"""Conan test_package — lbrate 1.1.

lbrate ships no tests and no test data, so test_lbrate.py builds spec-valid
CP/M LBR archives (a stored member and a squeezed member, with CRC-16 and CP/M
date stamps) and drives the packaged ``bin/lbrate`` against them: usage/getopt,
listing, wildcard selection, CRC test (good and corrupted), extraction and
decompression, raw ``-n`` extraction, plus two OHOS-specific checks (ELF
contract of the delivered binary; utime() timestamp restoration on the OHOS
file system).  The script exits non-zero on any failed assertion, which makes
self.run() raise.
"""
import os
import sys

from conan import ConanFile


class LbrateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "lbrate")
        script = os.path.join(self.source_folder, "test_lbrate.py")
        workdir = os.path.join(self.build_folder, "lbrate-test")
        self.run('"{}" "{}" --bin "{}" --workdir "{}"'.format(
            sys.executable, script, binary, workdir), env="conanrun")
