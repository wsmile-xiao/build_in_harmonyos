#!/usr/bin/env python3
"""Conan test_package — imlib2-heic 0.1.1 真实消费者 L1 校验。

imlib2-heic 是 dlopen 插件包（不提供链接库/头文件），test_package 从
安装包的 lib/imlib2/loaders/ heic.so 加载并校验公开 loader ABI 与
格式注册（heic/heif），见 test.c。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Imlib2HeicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 把安装包内插件绝对路径注入编译宏（仅当插件确实被打包时）
        pkg = self.dependencies["imlib2-heic"].package_folder
        plugin = os.path.join(pkg, "lib", "imlib2", "loaders", "heic.so")
        self.output.info(f"test_package plugin path: {plugin} exists={os.path.exists(plugin)}")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["imlib2-heic"].package_folder
        plugin = os.path.join(pkg, "lib", "imlib2", "loaders", "heic.so")
        if not os.path.exists(plugin):
            raise Exception(f"heic.so not packaged at {plugin}")
        # 以 shell 前缀把插件绝对路径注入环境变量（self.run 的 env 参数是
        # conan 环境名，不能直接传 dict，故拼入命令）
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_imlib2-heic")
        self.run(f'IMLIB2_HEIC_PLUGIN="{plugin}" "{binpath}"', env="conanrun")