#!/usr/bin/env python3
"""test_package for mpck 0.21 — real functional test (not --help).

Builds a minimal legal MP3 from an auditable base64 fixture, feeds it to
mpck, and asserts on exit code + output. See test.sh for details.
"""
import os

from conan import ConanFile


class MpckTestConan(ConanFile):
    """test_package for mpck — Checkmate MP3 checker CLI."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
