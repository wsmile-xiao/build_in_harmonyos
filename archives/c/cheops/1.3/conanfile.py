#!/usr/bin/env python3
"""Conan recipe — cheops 1.3 (autotools, C++ console chess)

CHEOPS (CHEss OPponent Simulator, Tristan Miller) is a small console chess
program: human/human, human/computer and computer/computer, alpha-beta
search, 64-square board.  This recipe adapts the 2016 GNU autotools release
to OpenHarmonyOS (aarch64).  It produces a single `cheops` binary (plus man
page + docs), so package_type = application (no library, no headers).

Upstream ships configure but NOT config.guess/config.sub, and the old
config.guess cannot recognise the OHOS build machine.  Modern FSF 2024
config.guess/config.sub (aarch64-aware) are bundled under files/ and copied
into the source tree before configure runs (same technique as the ncmpcpp
recipe); configure is then pinned with --build=aarch64-unknown-linux-gnu so
config.guess is never executed.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get,
                               replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CheopsConan(ConanFile):
    name = "cheops"
    version = "1.3"
    description = "CHEss OPponent Simulator — console chess program"
    license = "GPL-3.0-or-later"
    homepage = "https://logological.org/cheops"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle modern FSF config.guess/config.sub (aarch64-aware) so configure
        # can run on the OHOS device without guessing the build machine.
        copy(self, "*",
             os.path.join(self.recipe_folder, "files"),
             os.path.join(self.export_sources_folder, "files"),
             keep_path=True)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cheops supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _copy_gnu_config(self):
        """Drop modern config.guess/config.sub into the source root.

        The 2016 release tarball omits both; its generated configure locates
        them via ac_aux_dir ('.', since install-sh is at the top level).  The
        2024 config.sub understands aarch64; config.guess is kept for
        completeness but is never executed because we always pass --build.
        """
        for name in ("config.guess", "config.sub"):
            src = os.path.join(self.export_sources_folder, "files", name)
            dst = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                os.chmod(dst, os.stat(dst).st_mode | 0o111)
            else:
                self.output.warning(f"bundled {name} not found; configure may fail")

    def _fix_umask_077(self):
        # HMDFS: temp dirs that config.status/conftest create with umask 077 end
        # up without group-write permission, so writes fail. Relax to 022 (same
        # fix as the pakchois/en script/p11-kit recipes).
        for pattern in ("configure", "config.guess", "config.sub"):
            path = os.path.join(self.source_folder, pattern)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 022"))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess (even 2024) cannot guess OHOS from `uname -s=HarmonyOS`;
        # pin the full triplet instead. config.sub (2024) accepts aarch64.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def _drop_cxx17_register(self):
        # 2003-era C++ uses `register` as a storage hint; C++17 removed the
        # keyword and clang15 -std=c++17 (device profile cppstd) rejects it.
        # There is a single such use (ChessBoard.cpp is_white()). Removing the
        # specifier is semantics-preserving.
        path = os.path.join(self.source_folder, "src", "ChessBoard.cpp")
        if os.path.isfile(path):
            replace_in_file(self, path,
                            "register bool white=is_white",
                            "bool white=is_white")

    def build(self):
        apply_conandata_patches(self)
        self._copy_gnu_config()
        self._fix_umask_077()
        self._drop_cxx17_register()
        # Device default TMPDIR lives on HMDFS; point autotools conftest temp
        # files at a writable dir inside the conan build folder.
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # cheops is a CLI application, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
