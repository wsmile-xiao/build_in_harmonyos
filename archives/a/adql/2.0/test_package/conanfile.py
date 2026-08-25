#!/usr/bin/env python3
"""Conan test_package for adql 2.0 — 真实消费测试（python 脚本方式）。

显式 requires boost/1.90.0（adql 的传递依赖）——这样
self.dependencies["boost"] 可直接访问（ccapi 同款），cpp_info.
includedirs 返回绝对路径。
"""
from conan import ConanFile


class AdqlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    requires = "boost/1.90.0"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（build_folder 即归档 test_package 目录）——
        # 直接运行，不做 copy（避免 test_package/test_package/ 嵌套污染）
        pkg_folder = self.dependencies["adql"].package_folder
        # boost include 绝对路径（test_adql.cpp 的 ADQL/Query.hxx 内部
        # include boost/fusion 等头文件）
        boost_inc = ""
        b = self.dependencies["boost"]
        if b.cpp_info.includedirs:
            boost_inc = b.cpp_info.includedirs[0]
        self.run('python3 test_adql_run.py "%s" "%s"' % (pkg_folder, boost_inc),
                 env="conanrun")
