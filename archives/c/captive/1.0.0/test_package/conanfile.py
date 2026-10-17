#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run

class CaptiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["captive"].package_folder
        exe_name = (
            "captive-browser.exe"
            if str(self.settings.os) == "Windows"
            else "captive-browser"
        )
        bin_path = os.path.join(package_folder, "bin", exe_name)
        dns_path = os.path.join(package_folder, "bin", "systemd-networkd-dns")

        assert os.path.isfile(bin_path), (
            f"captive-browser binary not found: {bin_path}"
        )
        assert os.path.isfile(dns_path), (
            f"systemd-networkd-dns binary not found: {dns_path}"
        )

        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("sh")
                or "/bin/sh"
            )
            script = os.path.join(self.recipe_folder, "test_captive.sh")
            self.run(
                f'"{shell}" "{script}" "{bin_path}" "{dns_path}"',
                env="conanrun",
            )
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)

            assert magic == b"\x7fELF", (
                f"captive-browser is not an ELF binary: {magic!r}"
            )
            self.output.info(
                f"captive-browser binary exists and has ELF magic: {bin_path}"
            )
