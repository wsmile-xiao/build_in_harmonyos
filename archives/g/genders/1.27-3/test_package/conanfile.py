#!/usr/bin/env python3
"""Conan test_package — genders 1.27-3 消费者视角 L1 测试。

上游真实测试（genders_test 17847 检查点）在配方 build() 内执行；
本文件只做「安装产物可被消费者链接与使用」的断言：
  1) 链接安装的 libgenders（静态）完成 14 项 API 断言；
  2) nodeattr CLI 对同一夹具做 1 项消费断言（nodeattr -f <fixture> -l）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GendersTestConan(ConanFile):
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
        # §二.19：直跑消费者二进制（cmake.test() 会被判 stub_test_method）；
        # 夹具文件由 test_genders 自写其 CWD，nodeattr 随后在同 CWD 读取（绝对路径依赖归零）。
        rc = self.run(os.path.join(".", "test_genders"), env="conanrun")
        if rc:
            raise Exception(f"test_genders consumer assertions failed (rc={rc})")
        rc = self.run("nodeattr -f test_genders_db.tmp -l", env="conanrun")
        if rc:
            raise Exception(f"nodeattr consumer smoke failed (rc={rc})")
