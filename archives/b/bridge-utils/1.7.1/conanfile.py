#!/usr/bin/env python3
"""Conan recipe — bridge-utils 1.7.1 (Ethernet bridge control tools)

bridge-utils 提供 brctl 命令（C/autotools——Linux 网桥控制，netlink
直接 ioctl，无外部库依赖（标准 C + Linux 内核头 asm/param.h））。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BridgeUtilsConan(ConanFile):
    name = "bridge-utils"
    version = "1.7.1"
    description = "bridge-utils — utilities for configuring the Linux Ethernet bridge"
    license = "GPL-2.0-or-later"
    homepage = "https://www.linuxfoundation.org/collaborate/workgroups/networking/bridge"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # tarball 无 configure（configure.ac）→ autoreconf 生成 +
        # configure（--with-linux-headers 指定 OHOS 内核头——asm/param.h
        # 在 arch 子目录）+ make（CC=clang——OHOS 无 gcc）
        self.run(
            f"umask 000 && cd {src_dir} && "
            # tarball 无 configure——configure.ac 无 automake 宏（纯 autoconf，
            # aclocal/automake 未装——autoreconf 调 aclocal 失败）→ autoconf
            # 直接生成 configure + --with-linux-headers 指定 OHOS 内核头
            f"autoconf && "
            # configure 由 autoconf 生成（补丁无法应用）→ sed 修改生成
            # configure 的 mktemp umask 077→000（config.status 0700 目录
            # HMDFS 跨用户不可写——subs1.awk Permission denied，同 itstool）
            f"sed -i 's/umask 077 && mktemp/umask 000 \&\& mktemp/' "
            f"configure && "
            f"./configure --with-linux-headers="
            f"/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            f"sysroot/usr/include",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && "
            # -include limits.h（PATH_MAX 未声明——libbridge_devif.c 无
            # limits.h 且未间接引入）+ CC=clang（OHOS 无 gcc）
            f"make CC=/data/service/hnp/bin/clang "
            # -include limits.h（PATH_MAX）+ linux UAPI 宏（musl 头 vs linux
            # 头的 sockaddr_storage/in6_addr 双重定义——linux 头跳过这些
            # 定义用 musl 头的，同 glibc 的 __UAPI_DEF_* 机制）
            f"CFLAGS='-include limits.h -D__MUSL__' -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # brctl 可执行 + LICENSE
        copy(self, "brctl", src=os.path.join(src_dir, "brctl"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
