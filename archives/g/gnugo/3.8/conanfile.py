#!/usr/bin/env python3
"""Conan recipe — gnugo 3.8 (Autotools)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnugoConan(ConanFile):
    name = "gnugo"
    version = "3.8"
    description = "GNU Go - a Go (Weiqi/Baduk) playing engine"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnugo/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gnugo supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_config_status_tempdir(self, path):
        """Fix HMDFS temp dir creation: use TMPDIR and umask 022."""
        contents = load(self, path)
        if 'mktemp -d "${TMPDIR:-.}/confXXXXXX"' not in contents:
            replace_in_file(
                self, path,
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
            )
        if 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"' not in contents:
            replace_in_file(
                self, path,
                "tmp=./conf$$-$RANDOM",
                'tmp="${TMPDIR:-.}/conf$$-$RANDOM"',
            )
        if "(umask 022 && mktemp -d" not in contents:
            replace_in_file(
                self, path,
                "(umask 077 && mktemp -d",
                "(umask 022 && mktemp -d",
            )
        if '(umask 022 && mkdir "$tmp")' not in contents:
            replace_in_file(
                self, path,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and not cross_building(self):
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            # Patch config.sub to recognize ohos platform
            config_sub = os.path.join(self.source_folder, "config.sub")
            if os.path.isfile(config_sub):
                replace_in_file(
                    self, config_sub,
                    "gnu* | android* | bsd*",
                    "gnu* | android* | ohos* | bsd*",
                )
                replace_in_file(
                    self, config_sub,
                    "linux-gnu* | linux-dietlibc* | linux-android*",
                    "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-android*",
                )
            if not cross_building(self):
                self._patch_config_status_tempdir(
                    os.path.join(self.source_folder, "configure")
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
