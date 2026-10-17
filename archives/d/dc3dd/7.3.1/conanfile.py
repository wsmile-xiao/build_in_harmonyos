#!/usr/bin/env python3
"""Conan recipe for dc3dd 7.3.1.

dc3dd is a forensic imaging command-line utility derived from GNU dd. The
upstream release contains a generated Autotools build and its own gnulib
sources, so this package has no Conan library dependencies.
"""

import os
import shlex
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


SOURCE_URL = (
    "https://downloads.sourceforge.net/project/dc3dd/dc3dd/7.3.1/"
    "dc3dd-7.3.1.zip"
)
SOURCE_SHA256 = (
    "bd1b66d20a4020ab94b512e56d76cb5f86470d0216081586d596366927cb8d8b"
)
PATCHES = (
    "0001-config.guess-ohos.patch",
    "0002-config.sub-ohos.patch",
    "0003-configure-umask.patch",
    "0004-freadahead-musl.patch",
    "0005-freadptr-musl.patch",
    "0006-freadseek-musl.patch",
    "0007-fseterr-ohos.patch",
    "0008-pthread-cancel-ohos.patch",
)


class Dc3ddConan(ConanFile):
    name = "dc3dd"
    version = "7.3.1"
    description = "Forensic disk imaging utility with on-the-fly hashing"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/dc3dd/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dc3dd supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(
            self,
            url=SOURCE_URL,
            sha256=SOURCE_SHA256,
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-nls",
                "--disable-hdparm",
                "HELP2MAN=/bin/true",
                "MAKEINFO=/bin/true",
            ]
        )
        # Keep the four hash algorithms available in the installed CLI, which
        # is the feature set documented by the upstream release.
        tc.extra_cflags.extend(
            [
                "-DDEFAULT_HASH_MD5",
                "-DDEFAULT_HASH_SHA1",
                "-DDEFAULT_HASH_SHA256",
                "-DDEFAULT_HASH_SHA512",
            ]
        )
        tc.generate()

    def _apply_patches(self):
        patch_dir = os.path.join(self.export_sources_folder, "patches")
        for patch_name in PATCHES:
            patch(
                self,
                base_path=self.source_folder,
                patch_file=os.path.join(patch_dir, patch_name),
                strip=1,
            )

    def _make_release_helpers_executable(self):
        for relative_path in (
            "build-aux/config.guess",
            "build-aux/config.sub",
            "build-aux/git-version-gen",
            "build-aux/install-sh",
            "build-aux/missing",
        ):
            path = os.path.join(self.source_folder, relative_path)
            if os.path.isfile(path):
                mode = os.stat(path).st_mode
                os.chmod(
                    path,
                    mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                )

    def build(self):
        self._apply_patches()
        self._make_release_helpers_executable()

        # Autoconf 2.61 creates temporary directories with umask 077. On
        # HMDFS that can leave generated files inaccessible to the worker.
        if str(self.settings.os) == "OHOS":
            tmp_dir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            os.environ["TMPDIR"] = tmp_dir
            os.environ.setdefault(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )

        autotools = Autotools(self)
        configure_script = os.path.join(
            self.source_folder, "configure"
        ).replace("\\", "/")
        configure_shell = (
            "/system/bin/sh"
            if str(self.settings.os) == "OHOS"
            else (os.environ.get("CONFIG_SHELL") or "/bin/sh")
        )
        configure_tmp = os.environ.get(
            "TMPDIR", os.path.join(self.build_folder, "tmp")
        )
        # HMDFS may preserve release-tarball scripts as non-executable files.
        # Invoke configure through the selected shell instead of requiring +x.
        self.run(
            "cd {build} && TMPDIR={tmp} CONFIG_SHELL={shell} "
            "SHELL={shell} {shell} {configure} {args}".format(
                build=shlex.quote(self.build_folder.replace("\\", "/")),
                tmp=shlex.quote(configure_tmp.replace("\\", "/")),
                shell=shlex.quote(configure_shell),
                configure=shlex.quote(configure_script),
                args=autotools._configure_args,
            ),
            env="conanbuild",
        )
        make_args = [
            "-j1",
            "-o",
            "Makefile",
            "-o",
            "config.status",
            "ACLOCAL=/bin/true",
            "AUTOMAKE=/bin/true",
            "AUTOCONF=/bin/true",
            "AUTOHEADER=/bin/true",
        ]
        # The release man rule invokes its bundled Perl help2man script
        # directly and requires Locale::gettext. Build the code directories
        # explicitly; package() reuses the shipped dc3dd.1 instead.
        autotools.make(args=make_args + ["-C", "lib"])
        autotools.make(args=make_args + ["-C", "src"])

    def package(self):
        binary = os.path.join(self.build_folder, "src", "dc3dd")
        if not os.path.isfile(binary):
            raise ConanException(
                f"dc3dd binary was not produced: {binary}"
            )
        copy(
            self,
            "dc3dd",
            src=os.path.dirname(binary),
            dst=os.path.join(self.package_folder, "bin"),
        )
        shipped_man = os.path.join(self.source_folder, "man", "dc3dd.1")
        if not os.path.isfile(shipped_man):
            raise ConanException(
                f"upstream man page was not found: {shipped_man}"
            )
        copy(
            self,
            "dc3dd.1",
            src=os.path.dirname(shipped_man),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
