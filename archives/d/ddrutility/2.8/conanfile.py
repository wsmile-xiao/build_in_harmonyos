#!/usr/bin/env python3
"""Conan recipe — ddrutility 2.8 (raw makefile, C data-recovery tool set)

ddrutility 是一组配合 GNU ddrescue 使用的数据恢复辅助工具，产出 5 个命令行
程序：4 个 C 程序（ddrutility / ddru_ntfsbitmap / ddru_ntfsfindbad /
ddru_diskutility）+ 1 个 POSIX sh 脚本（ddru_findbad）。上游自 2.8 起由
automake 改为手写 makefile。路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DdrutilityConan(ConanFile):
    name = "ddrutility"
    version = "2.8"
    description = "Tool set for use with GNU ddrescue to aid in data recovery"
    license = "GPL-2.0-or-later"
    homepage = "https://ddrutility.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33：编译器取自 Conan conf，不用 shell 环境里的 ${CC}（release worker 上为空）。
        # 注：tools.build:compiler_executables 是 dict 值 conf，本机 Conan 2.29.1 不支持
        # `...:c` 子键写法（会抛 "does not exist in configuration list"），故整体取 dict。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        # 上游 makefile 写死 `CC= gcc`；命令行赋值优先级高于 makefile 赋值，
        # 因此 `make CC=<clang>` 即可覆盖，无需修改上游源码。
        # duplicate symbol 由 patches/0001+0002 从根上修（头文件全局变量改为
        # extern 声明 + 在 ddru_ntfscommon.c 单一定义），不使用 -fcommon 兜底。
        self.run(
            f"make CC={cc} CFLAGS='-O2 -Wall -W' -j1",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for prog in ("ddrutility", "ddru_ntfsbitmap", "ddru_ntfsfindbad", "ddru_diskutility"):
            copy(self, prog, src=self.source_folder, dst=bin_dir)
        # 上游以 ddru_findbad.sh 交付该 sh 脚本，makefile 的 install 规则把它装成
        # 无扩展名的 ddru_findbad；这里同样改名并显式补执行位。
        copy(self, "ddru_findbad.sh", src=self.source_folder, dst=bin_dir)
        os.rename(os.path.join(bin_dir, "ddru_findbad.sh"),
                  os.path.join(bin_dir, "ddru_findbad"))
        for prog in ("ddrutility", "ddru_ntfsbitmap", "ddru_ntfsfindbad",
                     "ddru_diskutility", "ddru_findbad"):
            os.chmod(os.path.join(bin_dir, prog), 0o755)

        copy(self, "*.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "ddrutility.info", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "info"))
        copy(self, "GPLv2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
