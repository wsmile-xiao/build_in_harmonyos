#!/usr/bin/env python3
"""test_package for cbqn: build a C consumer against the installed package and run it.

The consumer (test_cbqn.c) calls the public FFI in include/bqnffi.h - initialising the
interpreter, evaluating BQN source, passing C-built arrays through BQN functions and checking
21 concrete values - so the test genuinely fails when the shipped library is not functional.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class CbqnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        # 本机 create 带 user/channel、CI 用 plain reference，两种形态都要能解析
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        # run scope (conanrun.sh) is what test() consumes: libcbqn.so carries a DT_SONAME, so
        # the loader must resolve it through LD_LIBRARY_PATH rather than an embedded path
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 显式 self.run：ctest 执行编译并链接 libcbqn 的消费者程序（21 条 FFI 行为断言）
        self.run(
            "ctest --test-dir . --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
        )
