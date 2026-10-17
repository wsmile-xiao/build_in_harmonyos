#!/usr/bin/env python3
"""Conan test_package for xdg-dbus-proxy 0.1.7.

Verifies that the xdg-dbus-proxy binary is installed and runs correctly.
xdg-dbus-proxy is a command-line tool, so we test by running --version
and --help to confirm the binary is functional.
"""
import os

from conan import ConanFile


class XdgDbusProxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        bin_path = os.path.join(
            self.dependencies["xdg-dbus-proxy"].package_folder,
            "bin",
            "xdg-dbus-proxy",
        )

        assert os.path.isfile(bin_path), (
            f"xdg-dbus-proxy binary not found at {bin_path}"
        )

        # --version: should print "xdg-dbus-proxy 0.1.7" and exit 0
        self.run(f'"{bin_path}" --version', env="conanrun")

        # --help: should print usage text and exit 0
        self.run(f'"{bin_path}" --help', env="conanrun")
