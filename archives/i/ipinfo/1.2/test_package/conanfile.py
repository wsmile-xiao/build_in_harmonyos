#!/usr/bin/env python3
"""Conan test_package for ipinfo 1.2 — binary tool smoke test.

Verifies that the ipinfo and ipmatch binaries are installed and run correctly.
"""
import os

from conan import ConanFile


class IpinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ipinfo"].package_folder
        ipinfo_bin = os.path.join(pkg, "bin", "ipinfo")
        ipmatch_bin = os.path.join(pkg, "bin", "ipmatch")
        self.run(f'"{ipinfo_bin}" 192.168.1.0/24', env="conanrun")
        self.run(f'"{ipmatch_bin}" -t 192.168.1.100 192.168.1.0/24', env="conanrun")
