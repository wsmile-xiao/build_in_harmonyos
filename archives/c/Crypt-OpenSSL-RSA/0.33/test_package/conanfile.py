#!/usr/bin/env python3
"""test_package for Crypt-OpenSSL-RSA — verifies RSA.so and RSA.pm.

R34: Test must substantially depend on the tested package.
This test calls test_rsa.sh which verifies:
1. RSA.pm is syntactically valid Perl (perl -c)
2. RSA.so contains the XS boot symbol (readelf -s)
3. RSA.so links against OpenSSL (readelf -d NEEDED)
4. RSA.so is a valid ELF shared object
"""
import os

from conan import ConanFile


class CryptOpenSSLRSATestConan(ConanFile):
    """test_package for Crypt-OpenSSL-RSA — verifies XS module build."""
    test_type = "explicit"

    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["crypt-openssl-rsa"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(self.source_folder, "test_rsa.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
