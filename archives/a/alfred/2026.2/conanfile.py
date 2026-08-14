#!/usr/bin/env python3
"""Conan recipe for alfred 2026.2 — Almighty Lightweight Fact Remote Exchange Daemon.

alfred 是 batman-adv 网格网络的分布式信息共享守护进程/客户端（C，Makefile 构建），
产物 alfred（daemon+client）/batadv-vis（vis 可视化）。依赖：
- libnl-3 + libnl-genl-3（netlink，pkg-config 查找 libnl-3.0/libnl-genl-3.0）
  → libnl/3.7.0（ohpcd 已发布，配方带 pkg_config_name）
- libcap（capabilities，pkg-config 查找 libcap）→ libcap/2.69（ohpcd 已发布）
可绕过：gpsd 子程序（CONFIG_ALFRED_GPSD=n 禁用，无 gpsd 依赖）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AlfredConan(ConanFile):
    name = "alfred"
    version = "2026.2"
    description = "Almighty Lightweight Fact Remote Exchange Daemon (batman-adv)"
    license = "GPL-2.0"
    homepage = "https://www.open-mesh.org/projects/alfred"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libnl-3/libnl-genl-3（pkg-config libnl-3.0/libnl-genl-3.0）→ libnl/3.7.0
        self.requires("libnl/3.7.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # libnl 的 .pc 文件 prefix=/（conan pkg_config 生成器行为）导致
        # pkg-config 返回错误路径，改用 Makefile 支持的 LIBNL_CFLAGS/
        # LIBNL_LDLIBS/LIBNL_GENL_* 变量直接传 conan 依赖路径（绕过 pkg-config）；
        # -D__MUSL__ 并入 LIBNL_CFLAGS：OHOS musl 的 sys/socket.h 用
        # #ifndef __MUSL__ 包裹 sockaddr_storage 定义，避免与 linux/socket.h
        # 重复定义冲突。⚠️ 不能用命令行 CFLAGS+= 传（会屏蔽 Makefile 内所有
        # CFLAGS += 追加，含 LIBNL_CFLAGS，导致 -I 丢失）；
        # CONFIG_ALFRED_GPSD=n 禁用 gpsd（无 gpsd 依赖）；
        # CONFIG_ALFRED_CAPABILITIES=n 禁用 capabilities（libcap 包未提供 .pc）
        nl = self.dependencies["libnl"]
        nl_inc = os.path.join(nl.package_folder, "include", "libnl3")
        nl_lib = os.path.join(nl.package_folder, "lib")
        self.run(
            f"make -j1 CC={cc} "
            f"LIBNL_CFLAGS='-I{nl_inc} -D__MUSL__' LIBNL_LDLIBS='-L{nl_lib} -lnl-3' "
            f"LIBNL_GENL_CFLAGS='-I{nl_inc} -D__MUSL__' LIBNL_GENL_LDLIBS='-L{nl_lib} -lnl-genl-3' "
            f"CONFIG_ALFRED_GPSD=n CONFIG_ALFRED_CAPABILITIES=n",
            cwd=self.source_folder,
        )

    def package(self):
        # 拷贝 alfred + batadv-vis + man page
        copy(self, "alfred", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        vis_dir = os.path.join(self.source_folder, "vis")
        if os.path.exists(os.path.join(vis_dir, "batadv-vis")):
            copy(self, "batadv-vis", src=vis_dir,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "alfred.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "LICENSES", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
