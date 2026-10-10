#!/usr/bin/env python3
"""test_package for opengl 4.6 — 消费者用例 + 鸿蒙专项测试。

消费者用例 (test_package.c): 模拟业务上层组件, 仅通过库已安装的公开头文件
(<GL/glcorearb.h>, <GL/glext.h>, <GLES2/gl2.h>, <GLES3/gl3.h>,
<KHR/khrplatform.h>) 使用公开 API (宏/类型/调用约定 typedef), 编译、
链接并运行, 输出可观察断言结果。
鸿蒙专项测试 (harmonyos_test.c): aarch64-ohos 平台语义校验
(64 位指针、非 _WIN32 空调用约定、khrplatform/GLenum 类型宽度)。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenglTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁: test() 必须含 self.run — 直接重跑两个测试二进制, 确保真实执行而非 stub
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_package"), cwd=bindir)
        self.run(os.path.join(bindir, "harmonyos_test"), cwd=bindir)
