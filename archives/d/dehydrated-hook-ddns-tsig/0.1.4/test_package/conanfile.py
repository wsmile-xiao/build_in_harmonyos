#!/usr/bin/env python3
"""Conan test_package for dehydrated-hook-ddns-tsig 0.1.4 — Conan L1 test.

Pure-Python application package: the test drives the installed hook script
and its vendored dnspython from the consumer side (no C/C++ to link).
"""
import os

from conan import ConanFile


class DehydratedHookDdnsTsigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["dehydrated-hook-ddns-tsig"].package_folder
        checker = os.path.join(os.path.dirname(__file__), "verify_hook.py")
        self.run(f'python3 "{checker}" "{package}"')
