#!/usr/bin/env python3
"""Conan test_package — pytorch 2.13.0 (libtorch) L1 consumer test.

Runs a small program that actually loads libtorch and performs a tensor
addition (R34: substantive dependency on the tested package). The binary is
run with the conanrun environment (VirtualRunEnv) so the packaged shared
libraries (libtorch.so / libtorch_cpu.so / libc10.so) are on the runtime
search path (E298); cmake.test()/CTest is not used because CTest does not
carry the conanrun runtime environment reliably for cross-built packages.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PytorchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS musl: define __MUSL__ so patched headers (e.g. Macros.h
        # __assert_fail) take the musl-compatible declaration, matching the
        # sysroot assert.h (the consumer toolchain doesn't define it by itself).
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_FLAGS"] = "-D__MUSL__"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.abspath(os.path.join(self.cpp.build.bindirs[0], "test_pytorch"))
        # The cross-linked .so files carry DT_NEEDED as relative paths
        # (../lib/libc10.so). musl resolves a NEEDED containing '/' against the
        # current directory, so run the consumer from the packaged lib dir —
        # there ../lib/ resolves back to lib/ itself — while still using the
        # conanrun env (VirtualRunEnv) for libc++_shared.so.
        lib_dir = os.path.join(self.dependencies["pytorch"].package_folder, "lib")
        self.run(f'cd "{lib_dir}" && "{test_bin}"', env="conanrun")

        # HarmonyOS 专项测试（R6）：测试自身以 uname(2) 运行时判定宿主平台，在
        # HarmonyOS 上校验平台身份、补丁 0004 的 musl ssize_t 可见性、补丁 0001 的
        # group_norm 迭代器路径，以及 OHOS aarch64 下的复数/整数算术（非 HarmonyOS
        # 宿主打印 SKIP 并以 0 退出）。与上面的消费者用例同样从打包 lib 目录启动。
        ohos_bin = os.path.abspath(os.path.join(self.cpp.build.bindirs[0], "test_pytorch_ohos"))
        self.run(f'cd "{lib_dir}" && "{ohos_bin}"', env="conanrun")
