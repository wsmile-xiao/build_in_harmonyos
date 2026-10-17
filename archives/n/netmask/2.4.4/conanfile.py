#!/usr/bin/env python3
"""Conan 2 recipe — netmask 2.4.4 (Autotools, C CLI tool, zero third-party deps).

产物: bin/netmask + share/man/man1/netmask.1（netmask.info 需 makeinfo/texinfo，
OHOS 构建环境无 texinfo → build 期以 MAKEINFO=true 固化跳过于 Makefile）。

铁律符合性:
  R33: 编译器从 self.conf (tools.build:compiler_executables) 取，不裸用 ${CC}。
  R26: netmask 仅产 bin 可执行、无 .so，与系统无同名冲突 → 不强制静态。
  R32: 本配方无需按 settings.os 分支（test_package 用 in ("Linux","OHOS")）。
  R49: 本包零 requires，无依赖注入。

关键适配记录 (2026-09-03 真实编译实测, notes.md 有完整记录):
  1. Debian orig tarball 不含预生成 configure/Makefile.in → 需自举。
  2. E114 (HMDFS): autoreconf 生成的 configure/config.status 用 umask 077 建临时
     目录失败（config.status: could not setup config files machinery）。
  3. ⚠️ 本机 HMDFS 限制：conan 构建进程(task)无法 kernel-exec 用户目录(~/.conan2、
     ~/tmp 等 HMDFS 挂载)下的 **文本 shebang 脚本**（execve EACCES/bad interpreter），
     但可 exec ELF 与 /data/service/hnp（hmfs 挂载）下脚本。因此：
     - 不用 `autoreconf -fi`（其内部 exec aclocal/automake wrapper 会 EACCES）；
     - 改用显式解释器调用：autoconf/autoheader 直接在 /data/service/hnp/bin
       （hmfs，可 exec），automake 用 `perl <pkg>/bin/.automake-real --libdir=...`
       显式执行（exectest 实测可行）；configure 用 `bash configure` 显式解释。
     - CI/其他无此限制环境下同样成立（显式解释器调用是通用做法）。
  4. config.guess 问题不存在：configure.ac 无 AC_CANONICAL_HOST，native 构建不触发。
  5. make check (TESTS=./testscript) 实测 26 个 check 全 ok。
  6. 构建 in-source（不设 layout 分离 build）：testscript 相对路径引用 ./netmask。

平台: HarmonyOS PC aarch64 (os=OHOS / arch=armv8 / clang 15 / musl)。
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

import os


def _drop_umask_077(path: str) -> None:
    """E114: HMDFS 下 config.status 建临时目录失败, 去掉 configure 内 umask 077.

    configure 由 build() 内 autoconf 生成（非上游源文件），运行时修补可行；
    与 archives/a/abiword-plugin-clarisworks/3.0.8 的 _drop_umask_077 同法。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class NetmaskConan(ConanFile):
    name = "netmask"
    version = "2.4.4"
    description = "IP 地址网络掩码格式化/换算与 CIDR 合并命令行工具 (netmask generator)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tlby/netmask"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # netmask 2.4.4 纯 C、零第三方依赖（仅 libc）。
        # ⚠️ 上游 main/2.4.5+ 已引入 libcheck，锁 2.4.4 规避。
        pass

    def build_requirements(self):
        # 自举 Makefile.in/configure 需要 automake（aclocal 宏）。autoconf 家族已由
        # /data/service/hnp 提供（profile buildenv PATH 含之）。automake/1.18 制品仓已发布。
        # 注意：本机 HMDFS 下 automake/aclocal wrapper（文本脚本）不可被 kernel-exec，
        # 配方内以 `perl <pkg>/bin/.automake-real` 显式调用（见 build()）。
        self.tool_requires("automake/1.18")

    def layout(self):
        # in-source 构建（testscript 相对路径引用 ./netmask 与 tests/）。
        # 不调用 basic_layout，避免 conan 分离 build 目录断相对路径。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 编译器从 conf 取（不裸用 ${CC}）；无 requires → 无依赖注入（R49）。
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器必须从 Conan conf 获取，不能用 shell 环境变量（CI 上为空）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        src = str(self.source_folder)
        sh = "/data/service/hnp/bin/bash"

        # ① 自举 configure + Makefile.in（tarball 无生成物；aclocal.m4 为 1.14 旧版）。
        #    autoconf/autoheader 位于 /data/service/hnp/bin（hmfs，可直接 exec）；
        #    aclocal/automake 是文本 perl wrapper，kernel-exec 在本机 HMDFS 受限，
        #    故以 `perl <pkg>/bin/.aclocal-real / .automake-real` 显式解释器调用。
        #    流程 = aclocal(1.18 重建 aclocal.m4) → autoconf → autoheader → automake。
        #    先定位 automake 包目录（tool_require 的 bin 已在 conanbuild PATH）。
        setup_env = (
            f'AMBIN="$(dirname "$(command -v automake)")" && '
            f'AMROOT="$(dirname "$AMBIN")" && '
            f'export PERL5LIB="$AMROOT/share/automake-1.18:${{PERL5LIB:-}}" && '
            f'ACLOCAL_CMD="/data/service/hnp/bin/perl $AMBIN/.aclocal-real '
            f'--automake-acdir=$AMROOT/share/aclocal-1.18 '
            f'--system-acdir=$AMROOT/share/aclocal" && '
            f'AUTOMAKE_CMD="/data/service/hnp/bin/perl $AMBIN/.automake-real '
            f'--libdir=$AMROOT/share/automake-1.18"'
        )
        # aclocal（重建 aclocal.m4，消除 tarball 内 1.14 与 1.18 的 AM_INIT_AUTOMAKE 版本不匹配）
        self.run(f'cd "{src}" && {setup_env} && eval "$ACLOCAL_CMD"',
                 env="conanbuild")
        # autoconf + autoheader
        self.run(f'cd "{src}" && {setup_env} && autoconf', env="conanbuild")
        self.run(f'cd "{src}" && {setup_env} && autoheader', env="conanbuild")
        # automake --add-missing（生成 Makefile.in + 补齐 aux 脚本）
        self.run(
            f'cd "{src}" && {setup_env} && eval "$AUTOMAKE_CMD" '
            f'--add-missing --copy --foreign',
            env="conanbuild")

        # ② configure（in-source，--prefix=/ 与 package DESTDIR 配合；
        #    MAKEINFO=true 固化使 make 不需 makeinfo）
        #    E114: autoconf 生成的 configure 内嵌 config.status 用 `umask 077 &&
        #    mktemp -d` 建临时目录，HMDFS 下 Permission denied —— 运行前去 umask。
        #    以 `bash configure` 显式解释执行（规避 HMDFS kernel-exec 文本脚本限制）
        cfg = os.path.join(src, "configure")
        if os.path.exists(cfg):
            _drop_umask_077(cfg)
        self.run(
            f'cd "{src}" && '
            f'CC="{cc}" {sh} ./configure --prefix=/ MAKEINFO=true',
            env="conanbuild")

        # ③ 编译（R9: -j1 串行）
        self.run(f'cd "{src}" && make -j1', env="conanbuild")

        # ④ 上游官方测试: make check = TESTS ./testscript（26 个 check，shell+diff）。
        #    ⚠️ automake test-driver 默认直接 kernel-exec ./testscript（#!/bin/sh），
        #    在本机 HMDFS conan task 下报 "bad interpreter: Permission denied"；
        #    用 LOG_COMPILER=<bash> 让测试经显式 shell 解释执行（实测 26/26 通过）。
        self.run(
            f'cd "{src}" && make check LOG_COMPILER="{sh}"',
            env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        # DESTDIR + --prefix=/ → package/bin/netmask + package/share/man/man1/netmask.1
        self.run(f'cd "{src}" && make install DESTDIR="{pkg}"', env="conanbuild")

    def package_info(self):
        # 命令行工具：无库文件，为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
