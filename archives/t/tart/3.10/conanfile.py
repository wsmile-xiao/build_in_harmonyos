#!/usr/bin/env python3
"""Conan recipe for LinuxTaRT 3.10.

LinuxTaRT is a small Autotools-based CLI tool. The upstream install rule uses
`install -D`, which is not guaranteed on OHOS, so packaging copies the binary
and docs manually after the build.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TartConan(ConanFile):
    name = "tart"
    version = "3.10"
    description = "LinuxTaRT command-line e-mail signature and random tagline generator"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/linuxtart/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tart 3.10 supports Linux and OHOS, got {self.settings.os}"
            )

    def _configure_args(self):
        return [
            "--prefix=/",
            "--enable-color=no",
            "--disable-ibeats",
        ]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

        for script in ["configure", "install-sh", "config.guess", "config.sub"]:
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                os.chmod(path, 0o755)

        configure_args = " ".join(self._configure_args())
        self.run(f'cd "{self.source_folder}" && sh ./configure {configure_args}', env="conanbuild")
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")

    def package(self):
        copy(
            self,
            "tart",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "tart.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "*.5",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man5"),
            keep_path=False,
        )
        copy(
            self,
            "tart.tags",
            src=os.path.join(self.source_folder, "misc"),
            dst=os.path.join(self.package_folder, "share", "tart"),
            keep_path=False,
        )
        copy(
            self,
            "*-distrib",
            src=os.path.join(self.source_folder, "misc"),
            dst=os.path.join(self.package_folder, "share", "tart"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
