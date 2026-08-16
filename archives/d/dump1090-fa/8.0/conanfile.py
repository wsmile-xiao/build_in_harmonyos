#!/usr/bin/env python3
"""Conan recipe — dump1090-fa 8.0（FlightAware Mode-S/ADS-B 解码器）。

Makefile 构建（非 autotools，无 configure 脚本）。产物为命令行工具：
dump1090 / view1090 / faup1090 / starch-benchmark（R38 → commands.json）。

依赖 ncurses/6.5（交互界面 interactive.c 无条件 #include <curses.h>，
OHOS 分支 Makefile 不设置 LIBS_CURSES，需显式传入；制品仓已发布静态包）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class Dump1090FaConan(ConanFile):
    name = "dump1090-fa"
    version = "8.0"
    description = "dump1090-fa — Mode-S/ADS-B 报文解码器（FlightAware fork）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/flightaware/dump1090"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，绝不使用 ${CC}
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        nc = self.dependencies["ncurses"].cpp_info
        inc_flags = " ".join(f"-I{p}" for p in nc.includedirs)
        lib_flags = " ".join(f"-L{p}" for p in nc.libdirs)
        # OHOS(uname=HarmonyOS) 不匹配 Makefile 的 Linux 分支：
        #   - 无 -lrt（OHOS libc 已提供符号，无需）
        #   - 无 -D_DEFAULT_SOURCE → M_PI 等 math.h 扩展常量不可见，需补
        #   - LIBS_CURSES 为空 → 显式传 -lncursesw（静态 ncurses 包）
        # R9: 始终 -j1
        self.run(
            f'make -j1 CC="{cc}" CPPFLAGS="-D_DEFAULT_SOURCE {inc_flags}" '
            f'LDFLAGS="{lib_flags}" '
            f'LIBS_CURSES="-lncursesw" DUMP1090_VERSION={self.version} '
            f'all faup1090',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for exe in ("dump1090", "view1090", "faup1090", "starch-benchmark"):
            src = os.path.join(self.source_folder, exe)
            if os.path.exists(src):
                copy(self, exe, self.source_folder, bin_dir, keep_path=False)
        lic_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic_dir, exist_ok=True)
        copy(self, "LICENSE", self.source_folder, lic_dir, keep_path=False)
        copy(self, "COPYING", self.source_folder, lic_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
