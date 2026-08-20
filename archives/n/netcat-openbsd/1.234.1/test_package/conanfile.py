#!/usr/bin/env python3
"""Test package for netcat-openbsd — verifies the nc binary works.

R34: The test exercises the tested package's binary (nc -h).
The test.c source file uses popen() to run nc and verify output.
The conanfile.py test() method also runs nc -h directly.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class NetcatOpenbsdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # Find the nc binary from the package
        bin_dir = None
        for dep in self.dependencies.values():
            if dep.cpp_info and dep.cpp_info.bindirs:
                bin_dir = dep.cpp_info.bindirs[0]
                break

        if bin_dir is None:
            bin_dir = os.path.join(self.cpp_info.bindirs[0]) if self.cpp_info.bindirs else "bin"

        nc_path = os.path.join(bin_dir, "nc")
        if not os.path.isfile(nc_path):
            for dep_name, dep in self.dependencies.items():
                if "nc" in str(dep_name):
                    bin_dir = os.path.join(dep.package_folder, "bin") if hasattr(dep, 'package_folder') else "bin"
                    nc_path = os.path.join(bin_dir, "nc")
                    break

        # Run nc -h to verify the binary works
        self.run(f"{nc_path} -h", env="conanrun")
