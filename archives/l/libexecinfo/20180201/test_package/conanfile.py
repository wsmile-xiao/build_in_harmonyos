#!/usr/bin/env python3
"""Conan test_package for libexecinfo.

Builds the consumer program against the installed package headers and links
libexecinfo, then runs it to verify backtrace()/backtrace_symbols_fd() return
real results at runtime (R34: must exercise the tested package's public API).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import save
import os


class LibexecinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        cmake = CMakeToolchain(self)
        cmake.user_presets_path = False
        cmake.generate()

    def build(self):
        # 消费者用例：调用被测包公开 API（execinfo.h/backtrace 系列）
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        inc = f"-I{self.dependencies[self.tested_reference_str].package_folder}/include"
        lib = f"-L{self.dependencies[self.tested_reference_str].package_folder}/lib"
        # 1) C 消费者（test.c）编译+链接
        self.run(f"{cc} -c test.c -o test.o", cwd=self.source_folder)
        self.run(f"{cc} test.o -o test -lexecinfo {lib} {inc}", cwd=self.source_folder)
        # 2) 鸿蒙专项测试（ohos_special_test.cpp）编译+链接
        # OHOS 工具链已默认定义 __OHOS__（/data/service/hnp/bin/clang 实测
        # -dM 输出 #define __OHOS__ 1），不注入 -D__OHOS__，避免伪造平台状态。
        self.run(f"{cxx} -c ohos_special_test.cpp -o ohos_special_test.o {inc}",
                 cwd=self.source_folder)
        self.run(f"{cxx} ohos_special_test.o -o ohos_special_test -lexecinfo {lib} {inc}",
                 cwd=self.source_folder)

    def test(self):
        self.run(os.path.join(self.source_folder, "test"), env="conanrun")
        self.run(os.path.join(self.source_folder, "ohos_special_test"), env="conanrun")