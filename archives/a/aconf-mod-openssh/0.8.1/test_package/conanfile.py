#!/usr/bin/env python3
"""Conan test_package for aconf-mod-openssh 0.8.1."""

import os

from conan import ConanFile


class AconfModOpensshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["aconf-mod-openssh"].package_folder

        module_file = os.path.join(
            pkg_folder,
            "usr",
            "share",
            "lua",
            "5.4",
            "aconf",
            "modules",
            "openssh.lua",
        )

        self.run(
            f"ACONF_OPENSSH_MODULE=\"{module_file}\" "
            f"/system/bin/sh test_aconf_mod_openssh.sh",
            env="conanrun",
        )
