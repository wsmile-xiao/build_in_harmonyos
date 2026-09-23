#!/usr/bin/env python3
"""Conan recipe — nfcutils 0.3.2 (Autotools, single lsnfc tool).

nfcutils - NFC tools for POSIX (nfc-tools/nfcutils). Version 0.3.2 ships a
single tool `lsnfc` (list tags which are in your NFC device field). Pure C,
autotools build.

Consumes libnfc via pkg-config (configure.ac: PKG_CHECK_MODULES([libnfc],
[libnfc >= 1.7.0])).  libnfc 1.8.0 is a static library whose libnfc.pc has an
empty Requires, so the libusb-compat (libusb 0.1 API) and libusb-1.0 symbols
referenced by libnfc.a must be added explicitly at link time (same pattern as
the libnfc recipe's LIBS injection).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NfcutilsConan(ConanFile):
    name = "nfcutils"
    version = "0.3.2"
    description = "NFC tools for POSIX systems (lsnfc - list tags in NFC reader field)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nfc-tools/nfcutils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 要求 libnfc >= 1.7.0；仓内 1.8.0 满足
        self.requires("libnfc/1.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # configure 的 PKG_CHECK_MODULES([libnfc]) 需要 libnfc.pc 在
        # PKG_CONFIG_PATH 中（libnfc.pc 的 Requires 为空，但链接仍需
        # libusb-compat/libusb 的 -lusb/-lusb-1.0，见 LIBS 注入）。
        env = Environment()
        libs = []
        for dep in self.dependencies.values():
            pkgconfig = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig)
            for inc in dep.cpp_info.includedirs:
                env.append("CPPFLAGS", "-I" + inc)
            for libdir in dep.cpp_info.libdirs:
                env.append("LDFLAGS", "-L" + libdir)
            for lib in dep.cpp_info.libs:
                libs.append("-l" + lib)
        # 静态 libnfc.a 引用 libusb-compat（libusb 0.1 API）与 libusb-1.0
        # 符号；libnfc.pc Requires 为空不会展开。把依赖（含传递 libusb）的
        # -l 注入 LIBS（链接命令行末尾，依赖者在前，拓扑序遍历保证顺序），
        # 确保 -lusb / -lusb-1.0 参与最终可执行文件链接。
        if libs:
            env.append("LIBS", libs)
        # configure 会执行 conftest 等测试可执行文件，依赖共享库目录需进入
        # LD_LIBRARY_PATH（libusb-1.0.so.0 等）。
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("nfcutils-deps-env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 命令行工具，非库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]