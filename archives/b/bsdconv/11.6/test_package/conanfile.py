#!/usr/bin/env python3
"""test_package for bsdconv 11.6 — L1 consumer test.

直接编译（不经 CMake）：bsdconv 是纯 Make 项目，test_package 直接用
profile 指定的 clang 编译 test.c 并链接 libbsdconv.so，避免 OHOS
profile 注入的 LD_LIBRARY_PATH 与本机 cmake 二进制的 libstdc++ 符号
冲突（cmake 符号重定位失败）。
"""
import os

from conan import ConanFile


class BsdconvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 无需 CMakeDeps/CMakeToolchain；直接编译
        pass

    def test(self):
        # 编译器取 profile 的 tools.build:compiler_executables（dict conf）
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")

        pkg = self.dependencies["bsdconv"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        shd = os.path.join(pkg, "share", "bsdconv")

        # 编译消费者测试程序（调用 bsdconv API + 端到端二进制测试）
        self.run(f"{cc} test.c -I{inc} -L{lib} -lbsdconv -o test_bsdconv")

        # bsdconv 运行期通过 BSDCONV_PATH 定位 share/bsdconv 模块目录；
        # LD_LIBRARY_PATH 由 conanrun 环境提供（libbsdconv.so）
        os.environ["BSDCONV_PATH"] = shd
        self.run("./test_bsdconv", env="conanrun")
