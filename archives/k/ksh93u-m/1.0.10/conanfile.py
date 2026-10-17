#!/usr/bin/env python3
"""Conan recipe — ksh93u-m 1.0.10 (custom AST Mamfile build system).

ksh93u+m is a POSIX-compatible KornShell by AT&T Research. It uses its own
build system driven by `bin/package` (AST Mamfile), NOT autotools/meson.

Build & packaging notes
-----------------------
* `bash bin/package quiet make` builds two variants under arch/<hosttype>/:
    - bin/            : flat (statically linked, only NEEDED libc.so)
    - dyn/bin + dyn/lib : dynamically linked against libshell/libast/libcmd/libdll
  We ship the flat variant so the package is self-contained (no runtime deps).
  `bin/package install` is NOT used because it installs the dyn variant.
* Single source patch (pure logic fix in env_init(), no __OHOS__ macro):
    0001-src-cmd-ksh93-sh-init.c.patch
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir, rename
from conan.tools.layout import basic_layout


class Ksh93UmConan(ConanFile):
    name = "ksh93u-m"
    version = "1.0.10"
    description = "KornShell 93u+m — POSIX-compatible shell by AT&T Research (includes shcomp)"
    license = "EPL-2.0"
    homepage = "https://github.com/ksh93/ksh"
    url = "https://github.com/ksh93/ksh"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # no external dependencies — libast/libcmd/libdll/libshell are bundled
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/1.0.10")
        # which has no file extension, so Conan's get() deduces filename "1.0.10"
        # and unzip() falls back to the zip decoder → BadZipFile.  Pass an explicit
        # *.tar.gz filename so unzip() selects the tar.gz decoder (same fix as
        # archives/a/abcmidi/20260609).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ksh93u-m-1.0.10.tar.gz")

    def build(self):
        # R32: settings.os must support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        apply_conandata_patches(self)

        # R33: compiler must come from Conan conf, not bare shell env vars
        cc_dict = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = cc_dict.get("c") or "clang"

        # Custom AST build system (Mamfile via bin/package)
        package = os.path.join(self.source_folder, "bin", "package")
        self.run(f'CC="{cc}" bash "{package}" quiet make', cwd=self.source_folder)

    def package(self):
        # Ship the flat (statically linked) ksh + shcomp — self-contained, libc only.
        flat_bins = glob.glob(os.path.join(self.source_folder, "arch", "*", "bin", "ksh"))
        if not flat_bins:
            raise Exception("package: no flat arch/*/bin/ksh found — build may have failed")
        flat_bin_dir = os.path.dirname(flat_bins[0])

        mkdir(self, os.path.join(self.package_folder, "bin"))
        copy(self, "ksh", flat_bin_dir, os.path.join(self.package_folder, "bin"))
        copy(self, "shcomp", flat_bin_dir, os.path.join(self.package_folder, "bin"))
        # pty 是上游安装集的一部分（bin/package install 会复制 dyn/bin/pty），
        # ksh 的 pty 特性/测试依赖它，一并打包。
        copy(self, "pty", flat_bin_dir, os.path.join(self.package_folder, "bin"))

        # man page
        man1 = os.path.join(self.package_folder, "share", "man", "man1")
        mkdir(self, man1)
        sh_src = os.path.join(self.source_folder, "src", "cmd", "ksh93")
        copy(self, "sh.1", sh_src, man1, keep_path=False)
        rename(self, os.path.join(man1, "sh.1"), os.path.join(man1, "ksh.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
