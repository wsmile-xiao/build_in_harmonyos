#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — mdocml 1.14.6（L1 消费者测试，双层）.

层 1（C API，7 断言）：直编 + 链接交付的 `libmandoc.a` 与传递 zlib，
   覆盖 `mandoc.h` 公开 API —— mchars 字符表 / unicode 映射 /
   roff 特殊字符解析 / 转义序列推进契约。
   形态取 4ti2/1.6.10 先例（**直编而非 CMake**：避免交叉编译下
   CMAKE_SYSTEM_NAME 的额外处置面；L0c 的 `.c` 源文件判据由本层满足）。

层 2（可执行件，10 断言）：跑已安装 `bin/` 的 mandoc / demandoc / soelim
   与 man、apropos、whatis、makewhatis 四别名，校验渲染输出、别名字节等同
   （上游 `$(LN) mandoc <alias>` 语义，本平台 LN=cp -f）、`.so` 展开，
   以及交付面 `lib/libmandoc.a` + 对外 8 头。

消费者断言合计 **17**（7 + 10），全部计入 PR 正文「鸿蒙特有测试」行
（不进上游 1427 分母）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.errors import ConanException


class MdocmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # ── 层 1：直编 + 链接 libmandoc.a（含传递 zlib）──────────
        incs, libdirs, rpaths = [], [], []
        for _ref, dep in self.dependencies.items():
            incs += ["-I" + os.path.join(dep.package_folder, p)
                     for p in dep.cpp_info.includedirs
                     if os.path.isdir(os.path.join(dep.package_folder, p))]
            for p in dep.cpp_info.libdirs:
                full = os.path.join(dep.package_folder, p)
                if os.path.isdir(full):
                    libdirs.append("-L" + full)
                    rpaths.append("-Wl,-rpath-link," + full)

        # R33：编译器从 conf 整取 dict 再索引，绝不读 shell 环境变量
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = comp.get("c") or "/data/service/hnp/bin/clang"

        # 显式 cwd=self.source_folder：默认 cwd 是 build_folder，而
        # test_mdocml.c 与产物都落在 source_folder（无 layout() 时二者通常
        # 同目录，但不依赖该巧合——4ti2 先例同款显式指定）
        self.run(f'{cc} -o test_mdocml test_mdocml.c '
                 f'{" ".join(incs)} {" ".join(libdirs)} {" ".join(rpaths)} '
                 f'-lmandoc -lz',
                 cwd=self.source_folder)

    def test(self):
        if not can_run(self):
            self.output.info("cross build: compile-only, runtime validated elsewhere")
            return

        # ── 层 1：C API 7 断言（产物由 build() 落在 source_folder）──
        api_exe = os.path.join(self.source_folder, "test_mdocml")
        if not os.path.isfile(api_exe):
            raise ConanException(f"missing consumer test binary: {api_exe}")
        self.run(f'"{api_exe}"', env="conanrun")

        # ── 层 2：已安装可执行件 10 断言 ────────────────────────
        pkg = self.dependencies["mdocml"].package_folder
        bindir = None
        for d in self.dependencies["mdocml"].cpp_info.bindirs:
            cand = os.path.join(pkg, d)
            if os.path.isdir(cand):
                bindir = cand
                break
        if not bindir:
            raise ConanException("mdocml package has no bin/ directory")

        for tool in ("mandoc", "man", "demandoc", "soelim"):
            exe = os.path.join(bindir, tool)
            if not os.path.isfile(exe):
                raise ConanException(f"missing packaged executable: {exe}")

        # 用绝对路径 bash 显式调用，**不依赖脚本可执行位**：
        # HMDFS 上 chmod +x 不持久、git add 恒记 100644（device-facts §一.27），
        # 若直接执行脚本在 CI checkout 后必得 127 假象。
        # 2048.c/aa3d test_package 同款先例（CONFIG_SHELL → HNP bash 5.3）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_bins.sh")
        self.run(f'"{bash}" "{script}" "{bindir}"', env="conanrun")
