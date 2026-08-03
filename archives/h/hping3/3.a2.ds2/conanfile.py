#!/usr/bin/env python3
"""Conan recipe — hping3 3.a2.ds2（网络测试工具）.

hping3 是一个网络工具，支持 TCP/UDP/ICMP 自定义报文发送、端口扫描、
防火墙探测等（类似 ping 但更强大）。
构建系统：自定义 configure + Makefile
平台：OHOS aarch64 / Linux
依赖：零外部运行时依赖（libpcap 可选，默认禁用）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class Hping3Conan(ConanFile):
    name = "hping3"
    version = "3.a2.ds2"
    description = "hping3 — 网络测试工具（TCP/UDP/ICMP 自定义报文）"
    license = "GPL-2.0-only"
    homepage = "http://www.hping.org/"
    url = "https://github.com/antirez/hping"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        pass  # 零外部依赖（禁用 TCL/libpcap）

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # 生成 conanbuild 环境（注入 CC 交叉编译器），供自定义 configure 脚本使用
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # 自定义 configure 脚本（非标准 autotools），生成 Makefile
        # 脚本使用 CC=${CC:=cc}，需显式注入编译器（R33：从 conf 获取，fallback 到 PATH）
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        self.run(f"CC={cc} ./configure --no-tcl", env="conanbuild")
        # make 也需显式传 CC（Makefile 中 CC?= 允许命令行覆盖）
        self.run(f"make -j{os.cpu_count() or 1} CC={cc}", env="conanbuild")

    def package(self):
        # 上游 install 目标硬编码 /usr/sbin/，不适用 DESTDIR，手动打包二进制
        copy(self, "hping3", self.build_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "docs/hping3.8", os.path.join(self.source_folder),
             os.path.join(self.package_folder, "share/man/man8"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
