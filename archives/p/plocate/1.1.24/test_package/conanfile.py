#!/usr/bin/env python3
"""test_package for plocate 1.1.24 — end-to-end consumer verification.

plocate ships no linkable library; the consumer contract is the CLI trio
(plocate / plocate-build / updatedb). This test builds a real database
from a plaintext file list and asserts search behavior and output of the
installed binaries.
"""
from conan import ConanFile


class PlocateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanrun")
