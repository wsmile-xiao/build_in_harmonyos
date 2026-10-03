#!/usr/bin/env python3
"""test_package — libtlx 0.6.1 的真实消费者测试（OHOS aarch64）。

两个可执行（都由 `test()` 里的 `self.run(..., env="conanrun")` 真实执行）：

  1. `consumer`          — 只用**已安装的包**（find_package(tlx) → tlx::tlx）
                           走一遍上游公开 API：version 宏、digest 四族标准向量、
                           string 算子族（split/trim/join/ssprintf/base64/escape）、
                           integer_log2、btree_set/btree_map、LruCacheSet/Map、
                           RingBuffer、SplayTree、CountingPtr、ThreadPool、
                           MultiTimer、timestamp、siphash 上游向量、
                           parallel_mergesort、multiway_merge。
  2. `ohos_special_test` — 鸿蒙平台专项（`#ifdef __OHOS__` 真实逻辑，非空壳）：
                           工具链宏/位宽/字节序探针、静态库跨编译单元符号链接、
                           musl pthread 多线程、setenv + 环境变量展开。

两二进制均静态链接 libc++（-static-libstdc++，见 CMakeLists.txt），免
LD_LIBRARY_PATH 直跑（OHOS 动态 libc++_shared.so 默认搜索路径不含
ohos-sdk 运行库目录——上游测试设备端真跑时即踩此坑，见 notes.md 表 2）。

计数口径与取数命令见同目录 MANIFEST.yml（四口径分列，不与上游分母混用）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibtlxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("can_run=False，跳过消费者执行")
            return
        bindir = self.cpp.build.bindirs[0]
        # 逐个直跑（PF3/R34：test() 必须 self.run 真实执行）
        self.run(f'"{os.path.join(bindir, "consumer")}"', env="conanrun")
        self.run(f'"{os.path.join(bindir, "ohos_special_test")}"', env="conanrun")
