#!/usr/bin/env python3
"""Conan test_package — crack 5.0a.

Upstream crack 5.0a (1996 sources) registers exactly one test target:
src/libdes/Makefile "test: all" -> ./destest (the libdes DES algorithm
self-test). That upstream test is built and executed inside the recipe
build() (Stage 4) and passes on the target (exit 0).

In addition, this package carries platform-specific (HarmonyOS) tests
that exercise the packaged binaries end to end:

1. dawg/xdawg roundtrip — pack a wordlist into the DAWG dictionary
   format and unpack it back, verifying the dictionary codec used by
   every crack run.
2. cracker functional run — feed a crypt(3) ciphertext of the known
   weak password "123456" to the packaged cracker via the kickdict
   dictionary machinery (run/dict + scripts generated from packaged
   dicts) and assert the password is recovered.

These tests run the real binaries on the target (cross) profile and
fail non-zero when the tool misbehaves.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["crack"]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.source_folder, "test_crack.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
