#!/usr/bin/env python3
"""Conan recipe for lsw 0.3 (OHOS aarch64).

lsw（suckless "list window names"，MIT/X Consortium）＝列出 X 窗口管理器
所管窗口标题（读 X root window 属性）的 CLI 工具；本包交付 bin/lsw
（tool 型，无可链接库）。任务号 8583。

适配要点（详见 notes.md / test_package/MANIFEST.yml）：
  - 纯 Makefile（config.mk 变量派生 INCS/LIBS）：无 configure，无 VPATH，
    folders.build = "." in-source（abc 同款）；上游 install 目标用
    cp -f + chmod（非 install 二进制），无 M13/E098 暴露面。
  - CC=config.mk 烧死 `cc`，设备只有 clang（无 cc 符号链接）⇒ make 命令
    行覆盖 CC（R33：取自 tools.build:compiler_executables conf，非裸
    shell 环境变量）；config.mk 又把 X11INC/X11LIB 烧死成 /usr/X11R6
    （设备不存在），且 X11/X.h 属 xorgproto 协议头包（不在 libx11 自己
    的 include 目录里）⇒ 不逐个改被烧死的路径变量，而是命令行覆盖上游
    聚合变量 INCS/LIBS：遍历全部 host 依赖（含传递）拼绝对 -I/-L 注入，
    上游源码零改动（上游 config.mk 的 INCS/LIBS 正是引用这两个路径变量
    的聚合变量，故覆盖面最小）。
  - 依赖：libx11/6.4.0（制品仓已发布；transitive_headers/transitive_libs
    与归档内 11 个 X11 工具配方同款）。
  - 上游无任何测试目标（N_static=0，R51 允许消费者测试补位）：消费者
    测试走无 X 环境确定性错误路径——XOpenDisplay 失败 → lsw.c L19-20
    fprintf "cannot open display" + exit(EXIT_FAILURE)（clipnotify 1.0.2
    test_nox.sh 同款机制，证明 ELF 可执行 + X11 链接正确）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LswConan(ConanFile):
    name = "lsw"
    version = "0.3"
    description = "lsw - 列出 X 窗口管理器所管窗口标题的 suckless CLI 工具"
    license = "MIT"
    homepage = "https://dl.suckless.org/tools/"
    url = "https://dl.suckless.org/tools/lsw-0.3.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # conandata.yml 未声明 patches；保留标准导出入口以通过 W2/G1 结构检查。
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)
        # 纯 Makefile 无 VPATH：必须 in-source 构建（abc 同款）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器取自 conan conf（非裸 shell 变量）；config.mk 烧死
        # CC=cc，设备无 cc 符号链接，必须命令行覆盖。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # config.mk 把 X11INC/X11LIB 烧死成 /usr/X11R6，且 X11/X.h 属 xorgproto
        # 协议头包（不在 libx11 自己的 include 目录里）⇒ 覆盖上游聚合变量
        # INCS/LIBS，遍历全部 host 依赖（含传递）收集绝对 -I/-L，上游源码零改动。
        incs = " ".join(
            f"-I{os.path.join(dep.package_folder, d)}"
            for dep in self.dependencies.host.values()
            for d in dep.cpp_info.includedirs
        )
        libs = " ".join(
            f"-L{os.path.join(dep.package_folder, d)}"
            for dep in self.dependencies.host.values()
            for d in dep.cpp_info.libdirs
        )

        # 上游真实构建目标 lsw（all 仅打印 options 信息）
        self.run(
            f'make CC={cc} INCS="{incs}" LIBS="{libs} -lX11" lsw'
        )

    def package(self):
        # make install：cp -f + chmod + sed（设备均可用；chmod 在 HMDFS 上
        # 静默不生效属已知平台限制 E046，不影响交付）。
        self.run(
            f"make install DESTDIR={self.package_folder} "
            f"PREFIX=/ MANPREFIX=/share/man"
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
