#!/usr/bin/env python3
"""test_package for libslz 1.2.1（R34：真实调用被测包 API + 执行被测包二进制）。

四段（31 条断言，全部打印 `ASSERT_OK <name>` 一行一条）：
  1. test_slz      — libslz C API（slz_init/slz_encode/slz_finish、gzip/zlib 封套、
                     CRC32/Adler32 标准向量、level 0 路径），写出 rt-input.bin 与 slz-*.out；
  2. zenc          — 已打包 zenc 二进制对同一输入做 3 格式 × 2 级别编码；
  3. roundtrip.py  — 用 python 标准库 zlib（独立实现）解码 9 份输出并逐字节比对，
                     外加已打包 zdec 对 gzip 位流的 dump 校验；
  4. check_asserts.py — 汇总两份断言日志：任一 ASSERT_FAIL 或断言数为 0 即失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibslzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        py = sys.executable or "python3"
        work = os.path.abspath(self.build_folder)
        bindirs = self.cpp.build.bindirs[0]
        test_bin = bindirs if os.path.isabs(bindirs) else os.path.join(work, bindirs)
        test_bin = os.path.join(test_bin, "test_slz")

        # 1) libslz C API 断言（写出 rt-input.bin / slz-*.out 到 work）
        self.run('"%s" "%s" > "%s" 2>&1' % (test_bin, work, os.path.join(work, "c-assert.log")),
                 env="conanrun")

        # 2) 已打包 zenc 二进制：3 格式 × 2 级别
        for fmt, tag in (("-G", "gzip"), ("-Z", "zlib"), ("-D", "deflate")):
            for lvl, suffix in (("-1", ""), ("-0", "-l0")):
                self.run('zenc %s %s "%s" > "%s"' % (
                    fmt, lvl, os.path.join(work, "rt-input.bin"),
                    os.path.join(work, "zenc-%s%s.out" % (tag, suffix))),
                    env="conanrun")

        # 3) 独立解码器 round-trip + zdec 位流 dump 断言
        rt = os.path.join(self.source_folder, "roundtrip.py")
        self.run('"%s" "%s" "%s" > "%s" 2>&1' % (
            py, rt, work, os.path.join(work, "py-assert.log")), env="conanrun")

        # 4) 汇总把关：31 条断言、0 失败
        agg = os.path.join(self.source_folder, "check_asserts.py")
        self.run('"%s" "%s" "%s" "%s"' % (
            py, agg, os.path.join(work, "c-assert.log"),
            os.path.join(work, "py-assert.log")), env="conanrun")
