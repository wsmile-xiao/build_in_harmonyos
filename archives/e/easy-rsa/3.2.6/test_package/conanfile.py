#!/usr/bin/env python3
"""test_package for easy-rsa — verifies the easyrsa script is functional.

Runs test.sh which:
1. Checks `easyrsa --version` outputs the correct version
2. Runs `easyrsa init-pki` to verify PKI initialization
3. Runs `easyrsa build-ca nopass` to verify CA creation
"""
import os

from conan import ConanFile


class EasyRsaTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
