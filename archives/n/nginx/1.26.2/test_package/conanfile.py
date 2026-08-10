#!/usr/bin/env python3
"""Conan test_package for nginx — smoke test the binary.

Runs `nginx -V` and verifies the version output.
nginx is an application (not a library), so no compilation is needed.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class NginxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the nginx binary path from the dependency package folder
        nginx_dep = self.dependencies["nginx"]
        bin_path = os.path.join(nginx_dep.package_folder, "nginx", "sbin", "nginx")
        # Run nginx -V to verify the binary works
        self.run(f'"{bin_path}" -V', env="conanrun")
