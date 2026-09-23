#!/usr/bin/env python3
"""Conan recipe — libbpf 1.5.1 (custom Makefile build).

libbpf 使用自定义 src/Makefile（非 autotools/CMake）：
  make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1
OHOS 平台 BPF syscall 不可用，仅编译静态库（ELF 解析/BTF 等非 syscall 功能可用）。

适配要点（继承 1.6.2/1.4.5 历史经验 + 本次 1.5.1 实测）：
  1. 依赖 libelf（elfutils/0.195 已发布，含全部依赖链）与 zlib；
     必须把依赖的 -I/-L/-l 经环境变量喂给 Makefile（NO_PKG_CONFIG=1 跳过
     pkg-config 探测，路径只能由 CPPFLAGS/LDFLAGS 显式注入）。
  2. linux/socket.h 与 sys/socket.h 在部分 libc（含 OHOS SDK）上同时定义
     sockaddr_storage 导致 netlink.c 重定义冲突：patches/0001-src-netlink.c.patch
     用平台无关自守卫（#if !defined(_UAPI_LINUX_SOCKET_H) + #define + typedef
     __kernel_sa_family_t）先 include sys/socket.h 并跳过 linux/socket.h。
  3. make install 用 install(1)，OHOS 系统无该命令：PATH 注入 conan
     deps 工具或由 build 环境补齐（CI 的 ohos-aarch64 profile 已有工具链）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibbpfConan(ConanFile):
    name = "libbpf"
    version = "1.5.1"
    description = "Linux BPF subsystem user-space interaction library (ELF parsing available on OHOS)"
    license = "(LGPL-2.1 OR BSD-2-Clause)"
    homepage = "https://github.com/libbpf/libbpf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libelf（elfutils 提供）+ zlib：libbpf 的 ELF 解析依赖
        self.requires("elfutils/0.195")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 依赖的 -I / -L / -l 必须经环境变量喂给自定义 Makefile
        _inc, _lib, _l = [], [], []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            for _p in ci.includedirs or []:
                _inc.append("-I" + _p)
            for _p in ci.libdirs or []:
                _lib.append("-L" + _p)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        os.environ["LIBS"] = " ".join(_l) + " " + os.environ.get("LIBS", "")
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        # 构建期运行探测程序需要能找到依赖 .so：只影响进程执行，不进产物
        _ldpath = ":".join(_p for _dep in (d for _r, d in self.dependencies.items())
                           for _p in (_dep.cpp_info.libdirs or []))
        if _ldpath:
            os.environ["LD_LIBRARY_PATH"] = _ldpath + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            self.output.info("LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"][:200])

    def build(self):
        apply_conandata_patches(self)
        self.run("make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 -C src -j1",
                 cwd=self.source_folder)

    def package(self):
        # 只安装头文件 + 静态库 + pkgconfig
        self.run("make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 "
                 "-C src DESTDIR=%s PREFIX=/usr install" % self.package_folder,
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["bpf"]
        # make install 以 PREFIX=/usr + DESTDIR=package 安装：
        # 头文件在 usr/include，静态库在 usr/lib64（HOSTARCH=aarch64 → LIBSUBDIR=lib64）
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libdirs = ["usr/lib64"]
        self.cpp_info.set_property("pkg_config_name", "libbpf")
        # 静态链接时下游需带 libelf/zlib
        self.cpp_info.requires = ["elfutils::elfutils", "zlib::zlib"]
