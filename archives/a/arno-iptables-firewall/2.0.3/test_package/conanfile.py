#!/usr/bin/env python3
"""Conan test_package for arno-iptables-firewall 2.0.3.

Verifies that the packaged firewall scripts exist, are executable,
and contain the expected version string.
"""
import os
import shutil

from conan import ConanFile


class ArnoIptablesFirewallTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_arno_iptables_firewall.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )
