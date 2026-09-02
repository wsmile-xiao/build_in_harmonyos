#!/usr/bin/env python3
"""Conan recipe — libnfc 1.8.0 (Autotools).

依赖: libusb-compat/0.1.7（提供 libusb 0.1 API usb.h/libusb.pc → configure 的
PKG_CHECK_MODULES([libusb],[libusb]) 才能命中；本机无系统 libusb 0.1）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnfcConan(ConanFile):
    name = "libnfc"
    version = "1.8.0"
    description = "libnfc - Near Field Communication (NFC) library (1.8.0)"
    license = "LGPL-3.0"
    homepage = "https://github.com/nfc-tools/libnfc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libnfc 1.8.0 usbbus 使用 libusb 0.1 API (usb.h)，由 libusb-compat 提供
        self.requires("libusb-compat/0.1.7")

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
        # 文档生成需要 doxygen，CI/本机均无，显式关闭
        tc.configure_args.append("--disable-doc")
        tc.generate()
        # 依赖注入：configure 的 PKG_CHECK_MODULES([libusb],[libusb]) 需要
        # libusb.pc 在 PKG_CONFIG_PATH 中；AutotoolsToolchain 只 prepend
        # generators_folder，不会自动带依赖包的 pkgconfig 目录。
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
        # 静态链接 libusb-compat（libusb.a，0.1 兼容层）时其内部引用 libusb-1.0
        # 符号；Autotools 的 libtool 从 configure libusb_LIBS 只拿到 -lusb，
        # Requires.private 不会展开。把依赖（含传递 libusb/1.0.27）的 -l 注入
        # LIBS（位于链接命令行末尾），确保 -lusb-1.0 参与最终可执行文件链接。
        if libs:
            env.append("LIBS", libs)
        # conftest 等测试可执行文件运行时需要 libusb-1.0.so.0，
        # 依赖 libdir 必须进入 LD_LIBRARY_PATH（configure 会执行 conftest）。
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("libnfc-deps-env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libnfc.so → 链接名 nfc
        self.cpp_info.libs = ["nfc"]
