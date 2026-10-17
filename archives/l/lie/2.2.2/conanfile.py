#!/usr/bin/env python3
"""Conan recipe — lie 2.2.2（LiE 李群计算机代数系统，纯 C 裸 Makefile）。

要点（W0 四关证据：$TASK_DIR/w0/w0-evidence.md）：
  - 零外部依赖：readelf NEEDED 仅 libc.so；自带 bigint.c 478 行参与链接（W0 关②三层证真）
  - 构建 = `make noreadline`（设备/CI 无 readline，README 明文路径）+ 显式 CC
    （设备无 gcc/cc，先例#7）+ CFLAGS 钉桩（R33）
  - parser.c/parser.h 由 bison 3.8.2 构建期从 parser.y 生成（tarball 不带生成物，
    sage 源实测 parser 命中 0）—— 属构建期生成物，**不入补丁面**
  - 上游无 make check：三入口手跑（progs/test 23 断言 + progs/testsuite 18 条件断言
    + progs/maxsub0 纯定义装载 0 断言 = TOTAL 41），build() 内逐条计数、不符即失败
  - 0001 补丁：printexpr() fopen(NULL) 未检查 → OHOS /tmp EROFS 必 SIGSEGV(rc=139)，
    portability 补丁回退 stdout（对齐同文件 learn.c:135 先例），见 conandata
  - package() 直接 copy 收产物 + 自定位包装脚本（上游 make_lie 把构建目录绝对路径
    烧进 LD=，随包会断链，故重写为 dirname 自定位）
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 上游三入口的期望计数（W0 实测 2026-09-23/24，断言口径 = assertion 单栏）
_EXPECT_TEST_OKAY = 23          # progs/test：源 25 个 print 断言，#13/#15 上游注释 → 23 活
_EXPECT_TESTSUITE_TITLES = (    # progs/testsuite：3 行分节标题证明脚本跑完全程
    "recursie tests", "loop tests", "recursie in combinatie met loop tests",
)
_EXPECT_MAXSUB_SMOKE_LINES = 7  # maxsub0 载入 + print(Maxsub(A5)) → 7 个子群


class LieConan(ConanFile):
    name = "lie"
    version = "2.2.2"
    description = "LiE computer algebra package for Lie group computations"
    license = "LGPL-2.1-or-later"
    # 官方主页 young.sp2mi… 已下线（Apache 默认页/502，留档 w0/upstream-home.html）；
    # 填存活的发行版打包仓库（rule1 先例 astap-cli→Debian salsa；PF7 函数级模拟 classify=None）
    homepage = "https://salsa.debian.org/debian/lie"
    url = "https://salsa.debian.org/debian/lie"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 关②：硬依赖为空集（grep gmp/mpfr/mpir 三处 0 命中 + readelf NEEDED 仅
        # libc.so + bigint.c 在 common_objects 参与链接——三层证真，不需 conan 依赖）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # tarball 单一根目录 LiE/ → strip_root；有序 URL 列表（MIT 首选 RIKEN 回退）
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 上游测试驱动（在 build() 内真跑，证据直接进 conan create 日志 = CI L1 可读） ──
    def _capture(self, cmd, out_name):
        """在 source 树执行 cmd 并把输出写到 build 目录后读回；rc≠0 由 self.run 直接炸。"""
        out_path = os.path.join(self.build_folder, out_name)
        self.run(f'{cmd} > "{out_path}" 2>&1', cwd=self.source_folder)
        with open(out_path, encoding="utf-8", errors="replace") as fh:
            return fh.read()

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器取自 conf（整体 dict 再索引），回退 PATH clang 再回退 hnp 绝对路径
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = comp.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        # R9 固定 -j1；CFLAGS 钉桩（防 CI worker 环境泄漏 -fPIC/-O2 分叉 NDEBUG 面）；
        # noreadline = W0 关④ 裁定路径（设备无 readline；Makefile 默认目标 -lreadline 必挂）
        # bison 由 PATH 供给（/data/service/hnp/bin/bison 3.8.2，W0 关④「有」，worker
        # PATH 同含 /data/service/hnp/bin——device-facts §一.4）
        self.run(
            f"make -j1 noreadline CC={cc} CFLAGS='-O3 -pipe -DNDEBUG'",
            cwd=self.source_folder)

        sf = self.source_folder

        # ① progs/test —— 23 条 Okay 断言，0 false/error
        t1 = self._capture("./Lie.exe initfile . < progs/test", "up-test.out")
        okay = len(re.findall(r"^\s*\d+\s+Okay\s*$", t1, re.M))
        bad1 = [l for l in t1.splitlines()
                if l.strip() and "false" in l.lower() or "error" in l.lower() and l.strip()]
        if okay != _EXPECT_TEST_OKAY or bad1:
            raise ConanException(
                f"[upstream] progs/test 计数异常: Okay={okay}/{_EXPECT_TEST_OKAY}, "
                f"异常行={bad1[:5]}")

        # ② progs/testsuite —— 18 条条件断言（仅失败才 print error）+ 3 分节标题。
        #    只查 error==0 会把「空输出假绿」放行（device-facts §一.1），故必须同时
        #    断言三行标题在场 = 脚本真跑完全程。
        t2 = self._capture("./Lie.exe initfile . < progs/testsuite", "up-testsuite.out")
        low2 = t2.lower()
        missing = [s for s in _EXPECT_TESTSUITE_TITLES if s not in t2]
        if "error" in low2 or missing:
            raise ConanException(
                f"[upstream] progs/testsuite 异常: error 出现={'error' in low2}, "
                f"缺失分节标题={missing}, 输出行数={len(t2.splitlines())}")

        # ③ progs/maxsub0 —— 纯定义装载，成功 = 零输出；再用 A5 冒烟做正向证明
        #    （空输出本身无法区分「载入成功」与「什么都没干」，7 子群输出即正向证据）
        t3 = self._capture("./Lie.exe initfile . < progs/maxsub0", "up-maxsub0.out")
        if t3.strip():
            raise ConanException(
                f"[upstream] progs/maxsub0 应零输出，实得 {len(t3)} 字节: {t3[:200]!r}")

        smoke_in = os.path.join(self.build_folder, "smoke.li")
        with open(os.path.join(sf, "progs", "maxsub0"), encoding="utf-8",
                  errors="replace") as fh:
            defs_src = fh.read()
        with open(smoke_in, "w", encoding="utf-8") as fh:
            fh.write(defs_src)
            fh.write("\non gc\n\nprint(Maxsub(A5))\n")
        t4 = self._capture(f'./Lie.exe initfile . < "{smoke_in}"', "up-smoke.out")
        subs = [l for l in t4.splitlines() if l.strip()]
        if len(subs) != _EXPECT_MAXSUB_SMOKE_LINES:
            raise ConanException(
                f"[upstream] maxsub0 A5 冒烟异常: 期望 {_EXPECT_MAXSUB_SMOKE_LINES} 个子群, "
                f"实得 {len(subs)} 行: {subs}")

        self.output.info(
            "[lie-upstream] progs/test Okay=%d/23; progs/testsuite error=0 "
            "(18 条件断言, 3 分节标题在场); progs/maxsub0 载入 0 字节 + A5 冒烟 %d 子群 "
            "— TOTAL=41 PASS=41 FAIL=0 SKIP=0 NOT_RUN=0" % (okay, len(subs)))

    def package(self):
        """交付面 = bin/ 一个目录：二进制 + 数据文件 + 自定位包装脚本。

        数据文件必须与 Lie.exe 同目录：argv[2] 目录是 INFO.*/LEARN*/title 的查找根
        （init.c: strcpy(infofil,argv[2]) 后拼 INFO/.ind；print.c: sprintf("%s.%ld")）。
        """
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")

        copy(self, "Lie.exe", src, bindir)
        copy(self, "INFO.*", src, bindir)     # INFO.0-4（文档体）+ INFO.a（定义库）+ INFO.ind（索引）
        copy(self, "LEARN*", src, bindir)     # LEARN + LEARN.ind
        copy(self, "title", src, bindir)

        # 自定位包装：不烧绝对路径（上游 make_lie 烧 /bin/pwd 产物，conan cache 迁移即断链）。
        # $0 经 PATH 解析时是 execve 传入脚本的全路径 → dirname 即 bin/；相对调用补 pwd。
        wrapper = os.path.join(bindir, "lie")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/bin/sh\n"
                     'D=`dirname "$0"`\n'
                     'case "$D" in /*) ;; *) D=`pwd`/"$D" ;; esac\n'
                     'exec "$D/Lie.exe" initfile "$D"\n')
        # HMDFS：other 位不保（755→750），owner x 保留即同用户可执行；显式置位防 copy 丢 x
        os.chmod(wrapper, 0o755)
        os.chmod(os.path.join(bindir, "Lie.exe"), 0o755)

        # 反静默交付面断言（缺件即炸，清单进日志供 G4/审方核对）
        must = ["lie", "Lie.exe", "title",
                "INFO.0", "INFO.1", "INFO.2", "INFO.3", "INFO.4",
                "INFO.a", "INFO.ind", "LEARN", "LEARN.ind"]
        missing = [f for f in must if not os.path.isfile(os.path.join(bindir, f))]
        if missing:
            raise ConanException(f"[package] 交付面缺件: {missing}")
        self.output.info("[package] surface: " + ", ".join(sorted(must)))

    def package_info(self):
        # 可执行包：只有 bin/，清空 lib/include 面（G4 package_info↔包树对齐）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
