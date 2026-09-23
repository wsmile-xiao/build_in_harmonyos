#!/usr/bin/env python3
"""Conan recipe — libsidplayfp 2.15.1 (Autotools).

Uses the official release tarball (contains generated configure, libtool
2.4.7 and prebuilt psiddrv.bin, so no autoreconf/xa65 needed in CI).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsidplayfpConan(ConanFile):
    name = "libsidplayfp"
    version = "2.15.1"
    description = "libsidplayfp - a fork of libsidplay2, a C++ SID (MOS6581/MOS8580) chip emulator library"
    license = "GPL-2.0"
    homepage = "https://github.com/libsidplayfp/libsidplayfp"
    url = "https://github.com/libsidplayfp/libsidplayfp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 无 doxygen/makeinfo 时跳过文档生成
        tc.configure_args.append("MAKEINFO=true")
        # aarch64 上 long double 运算生成 __powidf2 等 compiler-rt 辅助符号，
        # 由 clang 的 builtins 运行时提供（见本地 make check 实证）
        tc.extra_ldflags.append("-lclang_rt.builtins")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sidplayfp", "stilview"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = []
