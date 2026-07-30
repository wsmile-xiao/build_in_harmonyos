#!/usr/bin/env python3
"""Conan recipe for GNU Chess 6.3.0."""
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


class GnuChessConan(ConanFile):
    name = "gnu-chess"
    version = "6.3.0"
    description = "GNU command-line chess engine"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/chess/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gnu-chess supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def _patch_config_status_tempdir(self, path):
        contents = load(self, path)
        if 'mktemp -d "${TMPDIR:-.}/confXXXXXX"' not in contents:
            replace_in_file(
                self,
                path,
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
            )
        if 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"' not in contents:
            replace_in_file(
                self,
                path,
                "tmp=./conf$$-$RANDOM",
                'tmp="${TMPDIR:-.}/conf$$-$RANDOM"',
            )
        if "(umask 022 && mktemp -d" not in contents:
            replace_in_file(
                self,
                path,
                "(umask 077 && mktemp -d",
                "(umask 022 && mktemp -d",
            )
        if '(umask 022 && mkdir "$tmp")' not in contents:
            replace_in_file(
                self,
                path,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and not cross_building(self):
            # Native OHOS workers may have a read-only config.guess temporary
            # directory.  Supplying the canonical tuple avoids that probe.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.configure_args.extend(
            [
                "--without-readline",
                "--disable-nls",
                "ac_cv_func_malloc_0_nonnull=yes",
                "ac_cv_func_realloc_0_nonnull=yes",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            config_sub = os.path.join(self.source_folder, "config.sub")
            replace_in_file(
                self,
                config_sub,
                "gnu* | android* | bsd*",
                "gnu* | android* | ohos* | bsd*",
            )
            replace_in_file(
                self,
                config_sub,
                "linux-gnu* | linux-dietlibc* | linux-android*",
                "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-android*",
            )
            if not cross_building(self):
                # HMDFS cannot use Autoconf's 077 temporary mode reliably.
                # Apply the repository's E011-compatible 022 mode.
                self._patch_config_status_tempdir(
                    os.path.join(self.source_folder, "configure")
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install(args=["-j1", "MAKEINFO=true"])

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
