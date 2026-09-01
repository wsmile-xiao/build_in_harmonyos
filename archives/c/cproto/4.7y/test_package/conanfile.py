#!/usr/bin/env python3
"""test_package for cproto — runs cproto on a C file to verify it works."""
from conan import ConanFile


class CprotoTestConan(ConanFile):
    """test_package for cproto — verifies the binary can parse C prototypes."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must actually execute the tested package's binary
        # and verify output contains expected prototypes
        self.run("cproto test.c | grep -q 'int add(int a, int b)'", env="conanrun")
