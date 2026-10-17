#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — mailto 1.3.2 消费者测试（CMake 构建 + popen 直读断言）。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会在 OHOS worker 上真实执行，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 用例只跑 -v / -h / 裸调用三种"不触碰网络与 sendmail"的路径，
  绝不构造真实 CGI 表单投递邮件。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class MailtoTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info(
                "cross-building: mailto 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not can_run(self):
            self.output.info("mailto runtime checks deferred to OHOS runner")
            return

        pkg = self.dependencies["mailto"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_mailto")
        self.run(f'"{exe}" "{pkg}"')
