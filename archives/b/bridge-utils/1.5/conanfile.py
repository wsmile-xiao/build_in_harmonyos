#!/usr/bin/env python3
"""Conan recipe for bridge-utils 1.5 (Ethernet bridge control tools)

bridge-utils 提供 brctl 命令（C/autotools，Linux 网桥控制，ioctl 直连，
标准 C 库，无外部依赖，路径 A 基础适配）。

与 1.7.1 的差异：
- 1.5 的官方发布包不在 kernel.org（kernel.org 仅提供 1.6/1.7.1 tar）；
  官方发布托管在 SourceForge project "bridge"（LFS 7.6 记录的权威下载
  源）。树内容与 git.kernel.org tag v1.5 逐字节一致（LF 归一化后，
  40/40 文件相同，已核对 MD5 ec7b381160b340648dede58c31bb2238）。
- 补丁 0001：libbridge.h 显式引入 sys/types.h + sys/time.h（musl 编译
  需要 u_int8_t/u_int16_t 别名与 struct timeval 定义，linux UAPI 头
  不间接引入）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BridgeUtilsConan(ConanFile):
    name = "bridge-utils"
    version = "1.5"
    description = "bridge-utils is a set of utilities for configuring the Linux Ethernet bridge"
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
        # SourceForge /download 与 ?viasf=1 均重定向到签名镜像→ 固定
        # filename 让 get() 正确解压（URL basename 含 /download、?viasf=1）
        get(self, **self.conan_data["sources"],
            filename="bridge-utils-1.5.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # 1.5 无 configure（configure.in）→ autoconf 直接生成 +
        # configure 的 --with-linux-headers 指定 OHOS 内核头（asm/param.h
        # 位于 arch 子目录）+ sed 修改 configure 的 mktemp umask（同 1.7.1）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"autoconf && "
            f"sed -i 's/umask 077 && mktemp/umask 000 \&\& mktemp/' "
            f"configure && "
            f"./configure --with-linux-headers="
            f"/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            f"sysroot/usr/include",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"make CC=/data/service/hnp/bin/clang "
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