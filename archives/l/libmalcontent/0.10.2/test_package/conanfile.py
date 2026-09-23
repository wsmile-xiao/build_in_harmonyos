#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 libmalcontent 核心 API。

test.c 真实调用 mct_app_filter_builder / mct_session_limits_builder /
serialize/deserialize 等核心 API（纯内存操作，不依赖 D-Bus 会话总线，
可在 OHOS 上完整运行）。test() 执行编译出的二进制并校验退出码。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmalcontentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # OHOS SDK 的 cmake/ninja 依赖 libc++_shared.so（位于
        # llvm/lib/aarch64-linux-ohos），不注入 LD_LIBRARY_PATH 则 cmake 启动
        # 报 "Error relocating ... symbol not found"（E012 变体）。
        ohos_llvm_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                         "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(ohos_llvm_lib):
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ohos_llvm_lib + (os.pathsep + cur if cur else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: 必须实际执行被测包二进制（非 print-only 空壳）
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libmalcontent")
        self.run(binary, env="conanrun")
