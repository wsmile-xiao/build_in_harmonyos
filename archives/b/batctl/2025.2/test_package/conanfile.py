#!/usr/bin/env python3
"""Conan test_package for batctl 2025.2.

R34: Test must actually depend on the tested package.
batctl is a CLI tool — the test runs the binary via test_batctl.sh.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BatctlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_libnl_dir(self):
        """Find directory containing libnl shared libraries."""
        dep = self.dependencies["batctl"]
        pkg_lib = os.path.join(dep.package_folder, "lib")
        candidate_dirs = [
            pkg_lib,
            os.path.join(os.path.expanduser("~"), "usr", "local", "lib"),
            "/usr/local/lib",
            "/usr/lib",
        ]
        for d in candidate_dirs:
            if os.path.isfile(os.path.join(d, "libnl-3.so.200")):
                return d
        return ""

    def test(self):
        # R34: Actually execute the tested binary via test_batctl.sh
        dep = self.dependencies["batctl"]
        batctl_bin = os.path.join(dep.package_folder, "bin", "batctl")
        test_script = os.path.join(self.source_folder, "test_batctl.sh")
        if can_run(self):
            # batctl dynamically links libnl (system dependency).
            # Set LD_LIBRARY_PATH so the binary can find libnl at runtime.
            lib_dir = self._find_libnl_dir()
            env_prefix = ""
            if lib_dir:
                existing = os.environ.get("LD_LIBRARY_PATH", "")
                if existing:
                    env_prefix = f'LD_LIBRARY_PATH="{lib_dir}:{existing}" '
                else:
                    env_prefix = f'LD_LIBRARY_PATH="{lib_dir}" '
            self.run(
                f'{env_prefix}sh "{test_script}" "{batctl_bin}"',
                env="conanrun",
            )
