#!/usr/bin/env python3
"""Conan test_package for unace 1.2b — consumer-side verification.

The upstream 1.2b tarball ships no test suite, so this test package builds a
minimal ACE v1.0 archive (stored entries, one nested under a subdirectory)
with mkace_test.py and drives the real binary through l / t / e / x, asserting
content equality and the tool's own CRC-check output.

ConanFile.run() returns None, so the pass/fail decision lives in
test_unace.sh (its exit code fails this test on any failed assertion).
"""
import os

from conan import ConanFile


class UnaceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["unace"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        unace_bin = os.path.join(bin_dir, "unace")

        archive = os.path.join(self.build_folder, "test.ace")
        work = os.path.join(self.build_folder, "work")
        os.makedirs(work, exist_ok=True)

        gen = os.path.join(self.source_folder, "mkace_test.py")
        driver = os.path.join(self.source_folder, "test_unace.sh")
        os.chmod(driver, 0o755)

        # build the fixture archive, then run the consumer assertions
        self.run(f'python3 "{gen}" "{archive}"', cwd=self.build_folder)
        self.run(f'"{driver}" "{unace_bin}" "{archive}" "{work}"', env="conanrun")
