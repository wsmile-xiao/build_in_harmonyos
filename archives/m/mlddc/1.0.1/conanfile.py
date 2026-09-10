#!/usr/bin/env python3
"""Conan recipe for mlddc 1.0 — Monolith 动态 DNS 客户端 (1997, C, Makefile)。

mlddc 是 Monolith (ml.org) 动态 DNS 服务的命令行客户端，纯 C + POSIX socket
(gethostbyname/socket/connect)，无 configure、无外部库依赖（非 SECURE 构建）。

OHOS 适配:
- 构建: 直接 clang 编译 mlddc.c/base64.c/netio.c（上游 Makefile 的 CFLAGS 含
  x86 专用 flag -m486/-malign-*，aarch64 clang 不适用），CFLAGS 追加
  -fgnu89-inline（netio.h 的 inline extern Disconnect 在 C99 下被两个 TU
  实例化导致重复符号, gnu89-inline 语义下只产生一个外部定义, 与 1997 年
  gcc 行为一致）;
- 编译器: 按 R33 从 Conan conf (tools.build:compiler_executables:c) 获取，
  不依赖 shell 环境变量;
- 测试: 运行 mlddc 验证可执行与退出码 (无输入时退出码 10 = Invalid user data,
  属预期错误路径, 验证程序本体可运行)。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MlddcConan(ConanFile):
    name = "mlddc"
    version = "1.0.1"
    description = "Client for the Monolith dynamic DNS service"
    license = "Freely Distributable"
    homepage = "https://github.com/OS2World/APP-INTERNET-mlddc"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，不依赖 shell 环境变量（CI worker 上为空）
        # tools.build:compiler_executables 是 dict conf（keys: c/cpp/...），须整体读取
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")
        # -fgnu89-inline: 修复 netio.h inline extern Disconnect 在 C99 下的重复符号
        cflags = "-O2 -Wall -fgnu89-inline"
        self.run(f"{cc} {cflags} -c mlddc.c -o mlddc.o")
        self.run(f"{cc} {cflags} -c base64.c -o base64.o")
        self.run(f"{cc} {cflags} -c netio.c -o netio.o")
        self.run(f"{cc} mlddc.o base64.o netio.o -o mlddc")

    def package(self):
        copy(self, "mlddc", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "mlddc"))

    def package_info(self):
        # 纯 CLI 工具：无可链接库目标，仅声明 bin 目录（R38 commands.json 配套）
        self.cpp_info.bindirs = ["bin"]
