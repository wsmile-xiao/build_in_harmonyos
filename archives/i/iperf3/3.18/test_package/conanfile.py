#!/usr/bin/env python3
"""Conan test_package for iperf3 3.18.

Runs iperf3 --version to verify the binary is functional.
iperf3 is a command-line tool, so we test by executing the binary.
"""
import os

from conan import ConanFile


class Iperf3TestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_iperf3.sh")
        iperf3_bin = os.path.join(pkg_folder, "bin", "iperf3")
        self.run(
            f'"{script}" "{iperf3_bin}"',
            env="conanrun",
        )
