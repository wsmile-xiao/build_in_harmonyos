#!/usr/bin/env python3
"""Conan test_package — fasttextembed 1.0.2.

L1 消费者验证（真实闭环）：仅通过已安装包（公开头 include/fte/fte.h、
正常链接目标 libfte.a、包内资源 vocab.tsv）编译、链接、调用公开 API
fte_init/fte_embed/fte_embed_batch，并验证 384 维可观测输出。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FasttextembedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # 消费者从包内 resdirs 取词表（运行时数据，随库安装产物分发）
        vocab = os.path.join(
            self.dependencies["fasttextembed"].package_folder,
            "share", "fasttextembed", "vocab.tsv")
        cmake.configure(variables={"VOCAB_PATH": vocab})
        cmake.build()

    def test(self):
        # L0d 门禁：test() 必须通过 self.run() 实际执行消费者二进制
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fasttextembed"),
                 env="conanrun")