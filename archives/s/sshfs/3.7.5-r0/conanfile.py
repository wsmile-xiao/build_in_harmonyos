#!/usr/bin/env python3
"""Conan recipe for sshfs — SSH Filesystem (Meson).

Upstream: https://github.com/libfuse/sshfs
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout

import os
import re
import shutil


class SshfsConan(ConanFile):
    name = "sshfs"
    version = "3.7.5-r0"
    description = "SSH Filesystem — mount a remote filesystem over SFTP"
    license = "GPL-2.0-only"
    homepage = "https://github.com/libfuse/sshfs"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libfuse/3.18.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()
        self._patch_fuse_pkg_config()
        tc = MesonToolchain(self)
        # Map Conan build_type to Meson buildtype (R33: no hardcoded values)
        _bt_map = {"Debug": "debug", "Release": "release",
                   "RelWithDebInfo": "debugoptimized", "MinSizeRel": "minsize"}
        tc.project_options["buildtype"] = _bt_map.get(str(self.settings.build_type), "release")

        # Inject ar/ranlib into the Meson native file [binaries] section.
        # Meson defaults to `llvm-ar` for clang toolchains; on OHOS CI the
        # toolchain bin dir may not be on PATH, so point at the archiver that
        # lives next to the C compiler, falling back to PATH lookup (R33:
        # no hardcoded paths).
        self._inject_ar_ranlib(tc)
        tc.generate()

    def _inject_ar_ranlib(self, tc):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        for tool, fallback in (("ar", "llvm-ar"), ("ranlib", "llvm-ranlib")):
            candidate = compiler_executables.get(tool)
            if not candidate and bindir:
                candidate = os.path.join(bindir, fallback)
            if not candidate or not os.path.isfile(candidate):
                candidate = shutil.which(fallback) or shutil.which(tool)
            if candidate and os.path.isfile(candidate):
                tc.binaries[tool] = candidate

    def _create_glib_pkg_config_aliases(self):
        # glib 的 conan 包只生成 glib-2.0.pc（包含全部子库），但 sshfs 的
        # meson.build 单独依赖 gthread-2.0，需要为它生成别名 .pc 文件。
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gthread-2.0.pc": "gthread-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _patch_fuse_pkg_config(self):
        # libfuse 包的头文件在 include/fuse3/ 下，但其配方声明的 includedirs
        # 是 include/，导致生成的 fuse3.pc 的 includedir 指向 include/，
        # meson 编译 sshfs.c 时 `#include <fuse.h>` 找不到。上游 fuse3.pc
        # 的 includedir 实际是 include/fuse3，这里对齐之。
        fuse_pc = os.path.join(self.generators_folder, "fuse3.pc")
        if not os.path.isfile(fuse_pc):
            return
        with open(fuse_pc, encoding="utf-8") as source:
            content = source.read()
        patched = re.sub(
            r"^includedir=.*$",
            "includedir=${prefix}/include/fuse3",
            content,
            flags=re.M,
        )
        if patched != content:
            with open(fuse_pc, "w", encoding="utf-8") as target:
                target.write(patched)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # sshfs is a command-line tool, not a library
