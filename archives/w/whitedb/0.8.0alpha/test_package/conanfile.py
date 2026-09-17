#!/usr/bin/env python3
"""Conan test_package — whitedb 0.8.0alpha

L1 test: 直接调用 whitedb 公开 API 编译并运行 test.c（int/str 字段 roundtrip）。
不用 CMake——CI/本机构建环境下 /data/service/hnp/bin/cmake 依赖 libc++_shared.so
（位于 ohos-sdk llvm/lib/aarch64-linux-ohos/ 子目录），conan 构建环境注入的
LD_LIBRARY_PATH 指向 llvm/lib 根目录导致加载失败(Error 127)。直接用 clang
编译+链接规避该运行时依赖（同 alpine 等配方先例）。
"""
import os

from conan import ConanFile


class WhitedbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["whitedb"].package_folder
        src = os.path.join(self.source_folder, "test.c")
        test_bin = os.path.join(self.build_folder, "test_whitedb")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -I\"{inc}\" -L\"{lib}\" "
            f"-o \"{test_bin}\" \"{src}\" -lwgdb -lm",
            env="conanbuild",
        )
        self.run(f"\"{test_bin}\"", env="conanrun")
