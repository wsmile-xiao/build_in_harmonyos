#!/usr/bin/env python3
"""Conan test_package for aescrypt-packetizer 3.16.

Terminal tool test — runs the aescrypt binary directly from the package.
"""
import os

from conan import ConanFile


class AescryptpacketizerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the aescrypt binary in the dependency's package folder
        for _, dep in self.dependencies.items():
            bin_path = os.path.join(str(dep.package_folder), "bin", "aescrypt")
            if os.path.exists(bin_path):
                self.run(f'"{bin_path}" --help')
                return
        # Fallback: try PATH
        self.run("aescrypt --help")
