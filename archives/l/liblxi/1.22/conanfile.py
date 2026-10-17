#!/usr/bin/env python3
"""Conan recipe — liblxi 1.22 (LXI instrument control library, Meson).

liblxi 提供 VXI-11 / raw / HiSLIP 三种协议的 LXI 仪器控制 API（lxi.h，
单一共享/静态库）。构建系统为 Meson；依赖 libxml2（解析 mDNS/Location）、
libtirpc（VXI-11 的 SunRPC，musl 无 rpc/rpc.h）、pthread（系统）。
avahi-client 为可选依赖（required: false），OHOS 环境无 avahi 头文件时
自动降级为无 mDNS 发现（mdns.c 空实现路径）。

上游测试清点（R51）：meson.build 仅 subdir('src')/subdir('man')，未注册
任何 meson test 入口；test/ 下 4 个程序均为未注册的手工示例，且都需要
局域网内真实 LXI 仪器（mDNS 发现 / SCPI 会话），设备与 CI 均无仪器可连。
故本包由 test_package 消费者测试承载验证（本地回环 RAW 协议全链路）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiblxiConan(ConanFile):
    name = "liblxi"
    version = "1.22"
    description = "Library for managing LXI compatible test instruments (VXI-11/raw/HiSLIP)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/lxi-tools/liblxi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # PkgConfigDeps 为 libxml2/libtirpc 生成 .pc；meson 的
    # dependency('libxml-2.0'|'libtirpc') 通过 pkg-config 解析。
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已实测远端二进制可用（conan install --build=never，2026-09-18）
        self.requires("libtirpc/1.3.7")
        self.requires("libxml2/2.15.3.1")

    def validate(self):
        # R32: 平台判断用 in，不用 == "Linux"
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"liblxi not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ── 工具链修复（与 at-spi2-core/glib2 配方一致）────────────────
        # CI worker 会把 AR/AS/STRIP/NM/RANLIB 导出为 llvm-* 裸名，meson 的
        # archiver 探测用裸名在 PATH 里找不到 → configure 报
        # "Unknown linker(s): llvm-ar"。弹出这些变量并锁定真实工具（绝对路径）。
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游未注册任何 meson test 入口（见文件头清点），无 meson test 可跑；
        # 验证由 test_package 消费者测试承载（真机运行，行为断言）。

    def package(self):
        meson = Meson(self)
        meson.install()
        # 实测（2026-09-18，llvm-readelf -S）：meson install 复制的产物保留
        # 链接期自签的 .codesign 段，无需 E077 重签；static 交付无运行时 ELF。

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 上游 library('lxi')（补丁后）：static 交付 liblxi.a / shared 交付 liblxi.so
        self.cpp_info.libs = ["lxi"]
