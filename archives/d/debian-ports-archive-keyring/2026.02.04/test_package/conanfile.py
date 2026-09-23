#!/usr/bin/env python3
"""Conan test_package — debian-ports-archive-keyring.

Validates the packaged keyring data without gpg/network:
  - required files present under share/keyrings/
  - every file byte-identical to the official Debian binary .deb (sha256)
  - ASCII-armor structure + OpenPGP packet parse + v4 key fingerprint
    (2 active keys, 19 removed keys).
These are Harmony-specific package/data validations (upstream has no test suite).
"""
import os

from conan import ConanFile


class KeyringTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-ports-archive-keyring"].package_folder
        keydir = os.path.join(pkg, "share", "keyrings")
        script = os.path.join(self.source_folder, "test_verify.py")
        self.run(f"python3 {script} {keydir}", env="conanrun")
