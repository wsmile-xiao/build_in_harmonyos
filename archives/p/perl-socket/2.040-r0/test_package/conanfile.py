#!/usr/bin/env python3
"""Conan test_package — perl-socket 2.040-r0.

Delegates verification to test_socket.py which checks:
- Socket.pm presence and version
- Socket.so valid ELF + shared object
- Dynamic dependency analysis (only libc.so expected)
- Perl module loading (best-effort, SELinux fallback)
"""
import os

from conan import ConanFile


class PerlsocketTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-socket"]
        pkg_folder = dep.package_folder
        self.output.info(f"Package folder: {pkg_folder}")

        so_path = os.path.join(pkg_folder, "lib", "auto", "Socket", "Socket.so")
        pm_path = os.path.join(pkg_folder, "lib", "Socket.pm")

        test_script = os.path.join(os.path.dirname(__file__), "test_socket.py")
        self.run(f'python3 "{test_script}" "{so_path}" "{pm_path}"')
