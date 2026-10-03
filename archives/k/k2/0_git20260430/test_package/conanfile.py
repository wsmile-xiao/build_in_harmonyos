#!/usr/bin/env python3
"""Conan test_package — verify the packaged k2 binary is functional.

k2 has no CLI flags; it speaks the UCI protocol on stdin/stdout, so the
consumer-level test runs test_k2.py against the packaged binary (same
pattern as the ympd smoke test): three UCI cases assert on the protocol
answers (R34: the test really executes the tested package's binary — the
L1e sabotage of bin/ makes the binary unresolvable and must fail this
test).
"""
import os
import sys

from conan import ConanFile


class K2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["k2"]
        binary = os.path.join(package.package_folder, "bin", "k2")
        script = os.path.join(self.source_folder, "test_k2.py")
        ret = self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
        if ret != 0:
            raise Exception("k2 UCI test suite failed")
