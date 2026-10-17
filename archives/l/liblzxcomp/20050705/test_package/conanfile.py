#!/usr/bin/env python3
"""Conan test_package — liblzxcomp 20050705.

两个测试都在本文件 test() 中真实执行：

1. `test.c`（鸿蒙特有消费者测试）
   内存后端构造 512KB 可压缩数据，调用真实 API
   lzx_init / lzx_compress_block / lzx_finish，断言压缩输出非空且小于输入。

2. `lzx_test.c`（上游官方自测程序，字节级原样复制，未改动一行）
   上游 2005 发行包自带的自测程序，对应上游 Makefile 的 lzx_test2 目标
   （即链接 liblzxcomp.a 的 lzx_test.c）。它以 stdin 读入明文、stdout 写出
   LZX 压缩流（前置 4 字节未压缩长度），stderr 打印压缩统计。
"""
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# conan settings.arch / platform.machine() 的常见别名归一到同一写法
_ARCH_ALIASES = {
    "armv8": "aarch64",
    "armv8.3": "aarch64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
    "amd64": "x86_64",
    "x86_64": "x86_64",
}


class LiblzxcompTestConan(ConanFile):
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

    def _target_runnable(self):
        """测试二进制能否在构建机上执行（host arch 与构建机 arch 一致即可）。"""
        machine = platform.machine().lower()
        target = str(self.settings.arch).lower()
        return (_ARCH_ALIASES.get(target, target)
                == _ARCH_ALIASES.get(machine, machine))

    def test(self):
        bindir = self.cpp.build.bindirs[0]

        if not self._target_runnable():
            self.output.info(
                f"cross-build host={self.settings.os}/{self.settings.arch} on "
                f"{platform.machine()}: 验编译+链接，运行放真机/CI")
            return

        # ── 1) 消费者测试（鸿蒙特有测试）─────────────────────────────
        self.run(os.path.join(bindir, "test_liblzxcomp"), env="conanrun")

        # ── 2) 上游自测程序 lzx_test.c（原样执行）─────────────────────
        # CMake 在配置阶段生成确定性语料 upstream_in.bin；上游 lzx_test.c
        # 要求 stdin 是可 seek 的普通文件（fseek/ftell 取输入总长度）。
        harness = os.path.join(bindir, "lzx_test2")
        corpus = os.path.join(bindir, "upstream_in.bin")
        packed = os.path.join(bindir, "upstream_out.bin")
        self.run(f'"{harness}" 15 < "{corpus}" > "{packed}"', env="conanrun")

        in_size = os.path.getsize(corpus)
        out_size = os.path.getsize(packed)
        # 上游在 stdout 前置 4 字节未压缩长度，故输出必须 > 4 且小于输入
        if out_size <= 4 or out_size >= in_size:
            raise ConanException(
                f"upstream lzx_test.c produced no compression: "
                f"in={in_size} out={out_size}")
        self.output.info(
            f"upstream lzx_test.c: PASS (in={in_size} out={out_size}, "
            f"ratio {100.0 - 100.0 * out_size / in_size:.2f}%)")
