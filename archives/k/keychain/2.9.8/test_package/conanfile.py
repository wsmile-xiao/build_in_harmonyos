#!/usr/bin/env python3
"""Conan test_package — keychain 2.9.8"""
import os
from conan import ConanFile

class KeychainTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        keychain_pkg = self.dependencies["keychain"].package_folder
        keychain_bin = os.path.join(keychain_pkg, "bin", "keychain")
        test_script = os.path.join(os.path.dirname(__file__), "test_keychain.sh")
        self.run(f"bash {test_script} {keychain_bin}", env="conanrun")
