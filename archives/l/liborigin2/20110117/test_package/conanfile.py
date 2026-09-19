#!/usr/bin/env python3
"""Installed-package consumer test for liborigin2 20110117."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Liborigin2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # liborigin2 的**公共头**直接 include boost 与 tree.hh
        # （OriginObj.h → boost/variant.hpp、OriginParser.h → tree.hh），
        # 因此真实消费者必须能自己找到这两者。这里显式声明，既让测试包能编译，
        # 也把"消费者的正确用法"固化成可执行示例。
        self.requires("boost/1.90.0.4.1")
        self.requires("tree-hh/3.18")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # 直接运行二进制而不是依赖 ctest：ctest 在"一个测试都没发现"时会
        # 返回 0，从而产生假绿（E249）。这里用真实进程的退出码作为唯一判据，
        # 找不到二进制就直接失败。
        candidates = [os.path.join(self.build_folder, "test_origin2")]
        candidates += glob.glob(
            os.path.join(self.build_folder, "**", "test_origin2"), recursive=True)
        binary = next((p for p in candidates if os.path.isfile(p)), None)
        if binary is None:
            raise ConanException(
                "test_origin2 binary not found under %s" % self.build_folder)
        self.output.info("[liborigin2] running consumer test: %s" % binary)
        self.run('"%s"' % binary, cwd=self.build_folder, env="conanrun")
