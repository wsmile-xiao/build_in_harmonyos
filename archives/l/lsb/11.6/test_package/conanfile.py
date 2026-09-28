#!/usr/bin/env python3
"""Consumer test for the installed lsb utilities."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class LsbTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building; skipping native lsb consumer test")
            return

        dep = self.dependencies["lsb"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        data_file = os.path.join(dep.package_folder, "share", "lsb", "distro-info", "debian.csv")
        # Conan 2 resolves ``env=`` to generated environment scripts, so hand the
        # consumer environment to the shell inline instead.
        env = (
            f'PATH="{bin_dir}{os.pathsep}$PATH" '
            f'PYTHONPATH="{bin_dir}" '
            f'LSB_DISTRO_INFO="{data_file}"'
        )

        self.run(f"{env} lsb_release -h")
        self.run(f"{env} lsb_release -i -s")
        self.run(f"{env} python3 -c \"import lsb_release, initdutils\"")
        init_functions = os.path.join(dep.package_folder, "lib", "lsb", "init-functions")
        self.run(f"{env} sh -c '. \"$1\"; log_warning_msg consumer-ok' sh {init_functions}")
        self.run(f"{env} sh -c 'install_initd >/dev/null 2>&1; test $? -eq 1'")
