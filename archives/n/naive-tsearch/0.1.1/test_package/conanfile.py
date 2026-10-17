#!/usr/bin/env python3
"""test_package — naive-tsearch 0.1.1 消费者验证（R34：真实调用被测包）

消费面 = 最终 Conan 包的两种交付形态，通过 CMakeDeps 找到包并链接：
1. 静态库形态：链接 libnaive-tsearch.a，走包装头 search.h → tsearch.h；
2. 头文件形态：定义 NAIVE_TSEARCH_HDRONLY 后包含同一 search.h，
   走 tsearch_hdronly.h（static 实现，TU 内自包含）。

两个形态各自跑 5 项行为断言（插入/重复插入复用节点/未命中/删除后
重查/twalk 遍历计数 + tdestroy 清理），合计 10 项可失败断言。
编译期断言保证用的是**包内**头而不是系统 <search.h>（防静默回落）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class NaiveTsearchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _consumer_binary(self):
        name = "naive-tsearch-consumer"
        candidates = []
        bindirs = self.cpp.build.bindirs
        if bindirs:
            first = bindirs[0]
            if os.path.isabs(first):
                candidates.append(os.path.join(first, name))
            else:
                candidates.append(
                    os.path.join(self.build_folder, first, name)
                )
        candidates.append(os.path.join(self.build_folder, name))
        for path in candidates:
            if os.path.isfile(path):
                return path
        raise AssertionError(
            "consumer binary not found; tried: " + ", ".join(candidates)
        )

    def test(self):
        if not can_run(self):
            return
        consumer = self._consumer_binary()
        # 真实运行消费者二进制（空壳/echo 形态会被 PF3 拦截）
        self.run(consumer, env="conanrun")
