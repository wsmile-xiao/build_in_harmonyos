#!/usr/bin/env python3
"""Conan test_package for ssl-cert-check — verifies the installed script works.

This test runs the ssl-cert-check binary with -V (print version) to verify
the package was installed correctly and the script is executable.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class SslCertCheckTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # env="conanrun" puts the package's bin/ on PATH
        # -V prints version info and exits with code 0
        self.run("ssl-cert-check -V", env="conanrun")
