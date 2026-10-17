#!/usr/bin/env python3
"""Conan 2 recipe — netmask 2.5.0 (Autotools, C CLI tool, upstream hard-depends libcheck).

产物: bin/netmask + share/man/man1/netmask.1（netmask.info 需 makeinfo/texinfo，
OHOS 构建环境无 texinfo → build 期以 MAKEINFO=true 固化跳过于 Makefile）。

2.4.4 → 2.5.0 关键变化（2026-09-04 真实编译实测, notes.md 有完整记录）:
  1. 上游 2.5.0 configure.ac 引入 `PKG_CHECK_MODULES([CHECK],[check])`，Makefile 链接
     $(CHECK_LIBS) → 新增硬依赖 check/0.15.2（制品仓 ohpcd 已发布 OHOS binary）。
     源码本身并不 #include <check.h>（纯链接需求）。配方链接指向 check 包内
     libcheck.a（静态归档），避免产出的 netmask 在运行时依赖 libcheck.so。
  2. 源码改用官方 release dist tarball（netmask-2.5.0.tar.gz，含预生成 configure /
     Makefile.in / aminclude_static.am），不再需要 2.4.4 的 automake 自举。
  3. 2.5.0 configure 会调用 config.guess 探测 build triple；本机/CI 均为 build=host=OHOS
     (aarch64)，config.guess 无法识别 `uname -s = HarmonyOS` → configure 显式传
     `--build=aarch64-linux-ohos`（config.sub 已支持该 triplet）。
  4. dist configure 同样内嵌 `(umask 077 && mktemp -d ...)`（E114，HMDFS 下
     config.status Permission denied）→ build() 运行时去掉 umask（同 2.4.4 处置）。
  5. make check (TESTS=./testscript) 实测 34 个 check 全 ok；testscript 以相对路径
     引用 ./netmask 与 tests/ → 构建必须 in-source。
  6. make check 的 test-driver 直接 kernel-exec testscript（#!/bin/sh）在本机 HMDFS
     conan 上下文被拒 → LOG_COMPILER=<hnp bash> 显式解释（同 2.4.4）。

铁律符合性:
  R32: test_package 用 settings.os in ("Linux","OHOS")，本配方无 os 分支。
  R33: 编译器从 self.conf (tools.build:compiler_executables) 取，不裸用 ${CC}。
  R26/R36: check 为制品仓第三方依赖（非系统同名库），动态链路由 conan 管理；
           CLI 自包含性要求 → 直接链 check 包内 libcheck.a（无符号引用，产物无
           NEEDED libcheck.so，静态与否均不影响，选择静态更稳妥）。
  R49: 依赖注入全部经 conan 生成物（PkgConfigDeps → check.pc），不写共享路径。

平台: HarmonyOS PC aarch64 (os=OHOS / arch=armv8 / clang 15 / musl；build=host=OHOS)。
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps

import os


def _drop_umask_077(path: str) -> None:
    """E114: HMDFS 下 config.status 建临时目录失败, 去掉 configure 内 umask 077.

    configure 随官方 release dist 分发（上游文件之一），但 umask 077 仅在 autoconf
    生成 configure 时写入、属 autoconf 通用逻辑；去掉后 configure 仍语义等价。
    同 2.4.4 先例（archives/n/netmask/2.4.4/conanfile.py `_drop_umask_077`）。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace("umask 077 && ", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class NetmaskConan(ConanFile):
    name = "netmask"
    version = "2.5.0"
    description = "IP 地址网络掩码格式化/换算与 CIDR 合并命令行工具 (netmask generator)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tlby/netmask"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 2.5.0 起 configure.ac: PKG_CHECK_MODULES([CHECK],[check]) —— 硬依赖。
        # 源码本身不 #include <check.h>；链接用包内静态归档（见 build()）。
        self.requires("check/0.15.2")

    def build_requirements(self):
        # 官方 release dist tarball 已含预生成 configure/Makefile.in → 无需 automake 自举。
        # configure 运行 PKG_CHECK_MODULES 需要 pkg-config 可执行：由 OHOS 工具链环境
        # （profile [buildenv] 注入 /data/service/hnp/bin）提供，与 2.4.4 用 hnp bash 同理。
        pass

    def layout(self):
        # in-source 构建（testscript 相对路径引用 ./netmask 与 tests/）。
        # 不调用 basic_layout，避免 conan 分离 build 目录断相对路径。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 为 check 生成指向真实包目录的 .pc（check 0.15.2 包内自带 check.pc 的 prefix
        # 指向构建临时目录、不可直接使用），输出到 generators_folder。
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，不能用 shell 环境变量（CI 上为空）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        src = str(self.source_folder)
        sh = "/data/service/hnp/bin/bash"

        # E114: dist configure 内嵌 `(umask 077 && mktemp -d ...)` → 去 umask。
        cfg = os.path.join(src, "configure")
        if os.path.exists(cfg):
            _drop_umask_077(cfg)

        # PkgConfigDeps 生成的 check.pc 位于 generators_folder → configure 时
        # PKG_CONFIG_PATH 指向它，PKG_CHECK_MODULES([CHECK],[check]) 才能命中。
        gendir = self.generators_folder

        # ① configure（in-source；--build 显式指定：config.guess 认不出 HarmonyOS）
        #    MAKEINFO=true 固化使 make 不需 makeinfo；bash 显式解释执行。
        self.run(
            f'cd "{src}" && export PKG_CONFIG_PATH="{gendir}" && '
            f'CC="{cc}" {sh} ./configure --build=aarch64-linux-ohos '
            f'--prefix=/ MAKEINFO=true',
            env="conanbuild")

        # ② 编译（-j1 串行；CHECK_LIBS 覆写为 check 包内静态归档，保证产物自包含：
        #    无 NEEDED libcheck.so；check 无符号被引用，静态归档不会引入额外依赖）
        check_lib = os.path.join(
            self.dependencies["check"].package_folder, "lib", "libcheck.a")
        self.run(f'cd "{src}" && make -j1 CHECK_LIBS="{check_lib}"',
                 env="conanbuild")

        # ③ 上游官方测试: make check = TESTS ./testscript（34 个 check，shell+diff）。
        #    LOG_COMPILER=<bash> 让测试经显式 shell 解释执行（HMDFS 限制，同 2.4.4）。
        self.run(
            f'cd "{src}" && make check CHECK_LIBS="{check_lib}" '
            f'LOG_COMPILER="{sh}"',
            env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        # 与 build()/make check 保持一致：install 亦覆写 CHECK_LIBS 为包内静态归档，
        # 防止任何触发重链接的时序回落 configure 默认 -lcheck（动态，NEEDED libcheck.so）。
        check_lib = os.path.join(
            self.dependencies["check"].package_folder, "lib", "libcheck.a")
        # DESTDIR + --prefix=/ → package/bin/netmask + package/share/man/man1/netmask.1
        self.run(f'cd "{src}" && make install DESTDIR="{pkg}" CHECK_LIBS="{check_lib}"',
                 env="conanbuild")

    def package_info(self):
        # 命令行工具：无库文件，为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
