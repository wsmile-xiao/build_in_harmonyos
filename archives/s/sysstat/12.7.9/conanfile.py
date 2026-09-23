#!/usr/bin/env python3
"""Conan recipe — sysstat 12.7.9 (Autotools)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SysstatConan(ConanFile):
    name = "sysstat"
    version = "12.7.9"
    description = "System performance monitoring tools (sar, iostat, mpstat, pidstat)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sysstat/sysstat"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable sensors support (HarmonyOS has no libsensors)
        tc.configure_args.append("--disable-sensors")
        # Disable NLS: clang 15 treats implicit gettext() declaration as error
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        # Fix HMDFS platform limitations (E046): config.status creates temp
        # subdirectories with umask 077 which HMDFS/SELinux blocks.
        # Replace umask 077 with umask 022 in configure (and config.status
        # template embedded within configure) so the generated config.status
        # also uses permissive umask.
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)
        # Also patch config.status if it exists (from a previous run)
        for fn in ["config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
