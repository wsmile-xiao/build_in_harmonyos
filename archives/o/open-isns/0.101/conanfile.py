#!/usr/bin/env python3
"""Conan recipe for open-isns 0.101."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenIsnsConan(ConanFile):
    name = "open-isns"
    version = "0.101"
    description = "iSNS server, client tools, and development library"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/open-iscsi/open-isns"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("open-isns supports POSIX platforms")

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

    def _patch_config_sub(self, path):
        replacements = (
            (
                "| arc | arm | arm[bl]e",
                "| aarch64 | arc | arm | arm[bl]e",
            ),
            (
                "| alphapca5[67]-* | alpha64pca5[67]-* | arc-*",
                "| alphapca5[67]-* | alpha64pca5[67]-* | aarch64-* | arc-*",
            ),
            (
                "linux-gnu* | linux-dietlibc | linux-uclibc*",
                "linux-gnu* | linux-ohos* | linux-dietlibc | linux-uclibc*",
            ),
            (
                "-mingw32* | -linux-gnu* | -linux-uclibc*",
                "-mingw32* | -linux-gnu* | -linux-ohos* | -linux-uclibc*",
            ),
            (
                "\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
                "\t-linux-ohos*)\n\t\t;;\n"
                "\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
            ),
        )

        contents = load(self, path)
        for original, replacement in replacements:
            if replacement in contents:
                continue
            if original not in contents:
                raise ConanException(
                    f"Cannot add OHOS support to unexpected config.sub: {path}"
                )
            replace_in_file(self, path, original, replacement)
            contents = load(self, path)

        if any(replacement not in contents for _, replacement in replacements):
            raise ConanException(f"Failed to add OHOS support to config.sub: {path}")

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and not cross_building(self):
            # Native OHOS workers cannot always execute config.guess because
            # its temporary directory may be read-only. Supplying the
            # canonical tuple avoids that probe while preserving cross builds.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.configure_args.extend(
            [
                "--without-security",
                "--without-slp",
                "--disable-shared",
                "--enable-static",
                "--with-rundir=/data/local/tmp/open-isns",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            config_sub = os.path.join(self.source_folder, "aclocal", "config.sub")
            self._patch_config_sub(config_sub)
            if not cross_building(self):
                # HMDFS cannot use Autoconf's 077 temporary mode reliably.
                # Apply the repository's E011-compatible 022 mode.
                self._patch_config_status_tempdir(
                    os.path.join(self.source_folder, "configure")
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(target="libisns.a", args=["-j1"])

    def package(self):
        copy(
            self,
            "libisns.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include", "libisns"),
            dst=os.path.join(self.package_folder, "include", "libisns"),
            keep_path=False,
        )
        copy(
            self,
            "paths.h",
            src=os.path.join(self.build_folder, "include", "libisns"),
            dst=os.path.join(self.package_folder, "include", "libisns"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["isns"]
        self.cpp_info.set_property("cmake_file_name", "open-isns")
        self.cpp_info.set_property("cmake_target_name", "open-isns::open-isns")
        self.cpp_info.system_libs = ["pthread"]
