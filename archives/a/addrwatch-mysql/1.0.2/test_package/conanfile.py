#!/usr/bin/env python3
"""Conan test_package — addrwatch-mysql 1.0.2

L1 test: verify the addrwatch_mysql binary is installed and can show help.
The binary is a shared-memory client that connects to a MySQL database.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AddrwatchMysqlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the addrwatch_mysql binary in the package folder
        pkg_folder = self.dependencies["addrwatch-mysql"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "addrwatch_mysql")
        if can_run(self):
            # Set LD_LIBRARY_PATH via the shell command itself (os.environ
            # may not propagate through Conan's conanrun environment).
            # Include: package lib (libmysqlclient.so copy), system libs,
            # mariadb-connector-c lib dir.
            prefix = os.path.expanduser("~/usr/local")
            mc = self.dependencies["mariadb-connector-c"]
            mc_lib = os.path.join(mc.package_folder, "lib", "mariadb")
            pkg_lib = os.path.join(pkg_folder, "lib")
            self.run(
                f'LD_LIBRARY_PATH="{pkg_lib}:{prefix}/lib:{mc_lib}" '
                f'"{bin_path}" --help',
                env="conanrun",
            )
