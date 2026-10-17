#!/usr/bin/env python3
"""razercfg 0.44 test_package — 消费者验证。

上游无测试（R51 清点确认），自研测试两层：
1. test_razercfg: 编译链接 librazer 库，断言 9 条 API 行为
   （razer_strlcpy 边界/截断/空串、razer_utf16_strlen、
   razer_ascii_to_utf16 转换及终止符，归为 6 组逻辑检查）。
2. razerd -v: 验证守护进程二进制在安装布局（bin/ + lib/）下可运行，
   输出版本帮助信息（退出码恒 0，见 test() 注释）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RazercfgTestConan(ConanFile):
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
        # 1) 库级 API 断言测试
        cmake = CMake(self)
        cmake.test()
        # 2) 守护进程可运行性验证：
        #    razerd.c 中 -v 分支调用 usage() 后返回 1，main() 内 `if (err > 0) return 0`
        #    → 进程实际退出码恒为 0（本地实测 exit=0），self.run 借退出码验证
        #    二进制在安装布局下可加载执行（NEEDED librazer.so + RUNPATH $ORIGIN/../lib）。
        #    注：usage 会向 stdout 打印 "Razer device service daemon"，CI 日志可见，
        #    此处不额外解析输出（conan self.run 不捕获 stdout 断言）。
        razerd_bin = os.path.join(self.dependencies["razercfg"].package_folder, "bin", "razerd")
        self.run(f"{razerd_bin} -v", env="conanrun")
