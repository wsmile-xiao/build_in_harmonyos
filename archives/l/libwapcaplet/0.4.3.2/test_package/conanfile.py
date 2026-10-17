#!/usr/bin/env python3
"""Conan test_package for libwapcaplet 0.4.3.2 — L1 smoke test.

CI runs this automatically via `conan create` (which invokes test_package).
test.c exercises the real lwc_string_* API of the package (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibwapcapletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # E120: OHOS SDK lld 链接 libxml2.so.16；把 SDK llvm 的 lib 目录
        # 注入 LD_LIBRARY_PATH，让 CMake configure/link 阶段能找到它
        # （CI worker 上该路径不在默认 loader 搜索路径）。
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(sdk_lib):
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34 / L0d (CI): test() 必须真正执行被测二进制（self.run），
        # 不能是空壳。先用 ctest 运行，再直接执行二进制双保险验证。
        cmake = CMake(self)
        cmake.test()

        # OHOS /system/bin/sh (mksh) 无法直接 exec ELF 二进制，用 bash 包裹
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libwapcaplet")
        self.run(f"{bash} -c '{exe}'", env="conanrun")
