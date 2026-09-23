#!/usr/bin/env python3
"""test_package/conanfile.py — libansilove 消费者测试"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibansiloveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run('"{}"'.format(exe), env="conanrun")
        # 鸿蒙 PC 专项：编译期 AArch64/musl 断言 + 真实 SGR ANSI 渲染 + 字体表索引
        exe_ohos = os.path.join(self.cpp.build.bindirs[0], "test_ohos")
        self.run('"{}"'.format(exe_ohos), env="conanrun")
        # ELF 层断言：SONAME/NEEDED(png,z,libc)/.codesign/无 RPATH/AArch64/musl
        # L1e 反向验证（R34）：剥掉被测包后 test 必须失败，证 test 真实依赖被测包
        pkg = self.dependencies["libansilove"].package_folder
        if pkg is not None:
            # ELF 断言仅对 shared 产物有意义；static 产物无 .so，跳过 ELF 段
            #（25 项功能测试 + 13 项 OHOS 测试已覆盖静态闭包正确性）
            if os.path.isfile(os.path.join(pkg, "lib", "libansilove.so")):
                self.run('bash "{}/test_elf.sh" "{}" "{}"'.format(
                    self.source_folder, pkg, self.cpp.build.bindirs[0]))
            else:
                self.output.info("static build: no libansilove.so, skip ELF checks")
