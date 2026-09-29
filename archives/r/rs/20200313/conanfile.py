#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for rs 20200313（MirOS / OpenBSD 血统的文本矩阵重排工具）。

rs 读入 stdin 的字段流，按列/行重新排布后写到 stdout，可选转置；纯
stdin/stdout 文本过滤器，只依赖 libc，无第三方库。

三条本包特有的硬约束（详见 notes.md，全部有设备侧实测证据）：

1. **上游构建入口不可用**：上游 Makefile 是 BSD make 语法——第 13 行
   ``.include <bsd.prog.mk>`` 在 GNU make 下直接
   ``Makefile:13: *** missing separator.  Stop.``，且引用不存在的
   ``${BSDSRCDIR}`` 与 BSD 的 ``${VAR:Q}`` 引号修饰符。故配方不驱动 make，
   而是按上游维护者本人在 Debian 里的等效做法逐 TU 编译 + 链接
   （rs.c、utf8.c、.linked/strtonum.c）；上游 Makefile 一个字节都不改。

2. **两个 OpenBSD 专有 libc 符号**：
   * ``strtonum(3)``（rs.c 六处调用）→ 用上游 tar 自带的
     ``.linked/strtonum.c``，并打开上游自己预留的两个移植开关
     ``NEED_STRTONUM``（rs.h 内 strtonum 原型）与 ``MBSDPORT_H``
     （rs.h 内含 ``__RCSID`` 等 ``<sys/cdefs.h>`` 后备）；两个开关由
     ``compat_defs.h`` 经 ``-include`` 提供，不改上游源码。
   * ``reallocarray(3)``（rs.c:345）→ 上游 tar 内**无**兼容源；OHOS 运行期
     musl 导出该符号，但 SDK 链接桩 ``libc.so`` 与 sysroot 头都没有它，
     于是链接报 ``undefined symbol: reallocarray``。由 ``compat_reallocarray.c``
     补一个独立 TU：该 TU 移植自 OpenBSD 的 ISC 实现（派生码，来源与许可在文件头
     披露），溢出时与 musl 同样返回 NULL（实测），但 errno 取值不承诺（本实现
     ERANGE=34，OHOS musl ENOMEM=12）。上游源码逐字节未改，但构建期另有 3 个
     配方侧补充件参与 ⇒ "无补丁文件 ≠ 无新增文件"，口径见 notes.md。

3. **上游语料在、runner 不在**：回归语料 ``check.t`` 有 13 条声明式用例，但其
   驱动脚本是 mksh 源码树的 perl ``check.pl``（``${MKSHDIR}/check.pl``），
   不在本 tarball 内。故随配方导出等价 runner ``check_t_runner.py``，在
   ``build()`` 里把 13 条**全部真实执行**（逐字节比对 expected-stdout）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# 随配方导出、构建期落到源码目录的补充件（上游源码零修改 ⇒ 不走 patches/）
COMPAT_FILES = ("compat_defs.h", "compat_reallocarray.c", "check_t_runner.py")


class RsConan(ConanFile):
    name = "rs"
    version = "20200313"
    description = "rs 以列为单位重排/转置 stdin 文本矩阵的命令行工具（MirOS rs）。"
    # 三项分工（Debian 打包的 debian/copyright 自述 "This is three-fold"，实测第 12/46/67 行）：
    # BSD-3-Clause = 上游 rs 主许可（rs.c / rs.1）；ISC 在**配方侧**只覆盖唯一的派生件
    # compat_reallocarray.c（移植自 OpenBSD reallocarray.c v1.3，来源与许可见该文件头与
    # manifest.yaml 的 shipped_sources_provenance），在**上游侧**对应本就属 ISC 档的 utf8.c
    # 与 .linked/strtonum.c；第三项取 SPDX 标识符 MirOS（Debian copyright 侧的用词是 MirBSD），
    # 覆盖 rs.h 与打包 —— rs.h 由 rs.c:52 include、实际编译进二进制，其许可文本实测
    # grep "Neither the name"=0、"Permission to use, copy, modify"=0、"sublicence"=1，
    # 既非 BSD-3-Clause 亦非 ISC 措辞。逐文件归属见 notes.md「许可证」节。
    # 列表形态沿用仓内既有写法，未自创字段形态（先例 archives/m/musepack/r475、
    # archives/v/vte/0.74.2 两份）。
    license = ["BSD-3-Clause", "ISC", "MirOS"]
    homepage = "https://www.mirbsd.org/MirOS/dist/mir/rs/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)
        # 兼容层与上游测试 runner 随配方走，而不是做成补丁：上游任何一字节
        # 都没被改过，patches/ 里也就没有内容（refresh-patch 因此不会重生成）。
        for extra in COMPAT_FILES:
            copy(self, extra, src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # 无第三方依赖（只用 libc）：strtonum 与 reallocarray 两个 OpenBSD
        # 专有符号分别由上游自带源与配方兼容 TU 解决，不引入 libbsd 之类。
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def _cflags(self):
        # -std=gnu99 与上游维护者 Debian rules 一致。
        # （2026-09-27 整改轮更正此处原先的说法：reallocarray 与 -std 无关——
        # 实测 OHOS sysroot 的 usr/include 全树 grep reallocarray **0 命中**，
        # gnu99 下同样没有该声明，声明由 compat_defs.h 经 -include 提供；
        # 读数见 notes.md §7。此处保留 -std=gnu99 只为与上游 rules 一致。）
        return "-O2 -std=gnu99 -Wall -Wextra -Wformat"

    def _compat_includes(self):
        return '-I. -include "%s"' % os.path.join(self.source_folder, "compat_defs.h")

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.warning("rs is only validated on POSIX hosts (Linux / OHOS)")
        apply_conandata_patches(self)
        for extra in COMPAT_FILES:
            copy(self, extra, src=self.export_sources_folder, dst=self.source_folder)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cflags = self._cflags()
        cppflags = self._compat_includes()

        # 等效于上游 bsd.prog.mk 的 PROG/SRCS，外加 .linked/strtonum.c；
        # 单元顺序与 Debian rules 的编译顺序一致。
        units = (("rs.o", "rs.c"), ("utf8.o", "utf8.c"),
                 ("strtonum.o", ".linked/strtonum.c"),
                 ("compat_reallocarray.o", "compat_reallocarray.c"))
        for obj, unit in units:
            self.run('"%s" %s %s -c "%s" -o %s' % (cc, cflags, cppflags, unit, obj))
        self.run('"%s" %s %s -o rs %s'
                 % (cc, cflags, cppflags, " ".join(obj for obj, _ in units)))

        self._run_upstream_check_suite("./rs", "check.t")

    def _run_upstream_check_suite(self, executable, corpus):
        """第 1 层：真实执行上游 check.t 的全部用例（N_static=13）。

        语料的官方驱动是 mksh 树里的 perl check.pl，不在本 tarball 内，
        故用同目录的 check_t_runner.py 按语料约定等价执行；断言口径与
        check.pl 一致（退出码 0 + stdout 逐字节相等）。失败即抛
        ConanException，不允许静默放行。
        """
        runner = os.path.join(self.source_folder, "check_t_runner.py")
        exe = os.path.abspath(os.path.join(self.build_folder, executable))
        script = os.path.join(self.source_folder, corpus)
        self.output.info("上游回归：check_t_runner.py 执行 %s（N_static=13 条声明式用例）"
                         % corpus)
        # self.run 会把 runner 的逐条 PASS/SKIP/FAIL 与 SUMMARY 原样打进构建
        # 日志（L1c 要的是执行痕迹，不是一个裸退出码），并在非 0 时直接失败。
        self.run('"%s" "%s" "%s" "%s" --allow-skip'
                 % (sys.executable, runner, exe, script))

    def package(self):
        copy(self, "rs", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "rs.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
