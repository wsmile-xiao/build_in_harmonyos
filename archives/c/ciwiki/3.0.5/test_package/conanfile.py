#!/usr/bin/env python3
"""Conan test_package — ciwiki 3.0.5 L1 consumer test.

ciwiki is a CLI wiki server binary.  Upstream ships no automated test
suite (make check has no registered tests), so this test_package provides
the functional assertions from a consumer's perspective:
  1. installed binary exists and is executable
  2. `ciwiki --version` prints the expected upstream version string
  3. `ciwiki --help` prints the usage/option list
  4. ciwiki can start as an HTTP server on 127.0.0.1 and serve a request
     against a temporary wiki home (smoke-level end-to-end check)
"""
from conan import ConanFile


class CiwikiTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["ciwiki"].package_folder
        self.run(f'bash test.sh "{pkg_folder}"', env="conanrun")
