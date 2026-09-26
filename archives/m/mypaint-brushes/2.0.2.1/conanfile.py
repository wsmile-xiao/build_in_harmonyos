#!/usr/bin/env python3
"""Conan recipe — mypaint-brushes 2.0.2.1 (pure brush-data package).

Pure autotools data package: brushes/*.myb + order.conf (7 brush groups,
196 brushes) plus share/pkgconfig/mypaint-brushes-2.0.pc. No C/C++
sources are compiled: `make all` and `make check` are both no-ops
(verified against this tarball: "Nothing to be done for 'all'/'check'",
exit 0). The recipe mirrors the upstream flow: source() fetches the
official release tarball, build() runs the (no-op) autotools build,
package() runs `make install` into the Conan package folder. The data
lands in share/mypaint-data/2.0/brushes and the pc file in
share/pkgconfig — exposed to consumers via cpp_info.resdirs,
cpp_info.defines (MYPAINT_BRUSHES_DIR, same as the upstream pc Cflags)
and PKG_CONFIG_PATH via buildenv_info.

Platform note: HarmonyOS HMDFS rejects writes into owner-only (0700)
directories created by `umask 077` inside autotools' config.status
(knowledge E011, same failure mode as xz/tar/wget). The single patch
rewrites configure's `umask 077` to `umask 022` (2 occurrences, config
temp-dir creation only) so `mktemp -d ./confXXXXXX` stays writable.
R38: data-only package — no commands.json needed (no executables).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MypaintbrushesConan(ConanFile):
    name = "mypaint-brushes"
    version = "2.0.2.1"
    description = "Brushes used by MyPaint and other software using libmypaint"
    license = "CC0-1.0"
    homepage = "https://github.com/mypaint/mypaint-brushes"
    url = "https://github.com/mypaint/mypaint-brushes"

    # 纯数据包显式声明 package_type="unknown"（对齐已合入纯数据包先例
    # kicad-demos 10.0.4 / linux-firmware-brcm）。零可执行文件 → 非
    # application 且 bindirs 为空，不触发 L0k/R38 commands.json 要求。
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero dependencies: pure brush data (brushes/*.myb + order.conf)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mypaint-brushes does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # `make all` is a no-op (data-only package); it still validates the
        # Makefile parse and brushes/ sub-Makefile wiring.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # --prefix=package_folder comes from AutotoolsToolchain; files land at
        # <pkg>/share/mypaint-data/2.0/brushes + <pkg>/share/pkgconfig/*.pc
        autotools.install()

    def package_id(self):
        # 纯数据包：内容与 settings 无关，清空 package id（kicad-demos 先例同款）。
        self.info.clear()

    def package_info(self):
        # Pure data package: no libs, no binaries, no headers.
        self.cpp_info.resdirs = ["share/mypaint-data/2.0/brushes"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Give consumers the upstream -DMYPAINT_BRUSHES_DIR define (same as
        # share/pkgconfig/mypaint-brushes-2.0.pc Cflags) without pkg-config.
        brushes_dir = os.path.join(
            self.package_folder, "share", "mypaint-data", "2.0", "brushes")
        self.cpp_info.defines.append(f'MYPAINT_BRUSHES_DIR="{brushes_dir}"')
        # Expose the installed pc file for pkg-config consumers.
        self.buildenv_info.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.package_folder, "share", "pkgconfig"))
