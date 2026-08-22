#!/usr/bin/env python3
"""Conan test package — cryptokit 1.21.1 C stubs layer SHA-256 API smoke test"""

import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run

class CryptokitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # R34: Actually compile test.c that calls SHA-256 API
        import os as _os
        # 修复：CMake 编译器测试（TryCompile 链接 cmTC_*）时 lld 依赖 libxml2.so.16 加载失败
        # （Error loading shared library libxml2.so.16）——设置 LD_LIBRARY_PATH 指向 lld 依赖库，
        # 并跳过编译器测试（CMAKE_C_COMPILER_WORKS）避免 TryCompile 链接失败。
        for d in ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
                  "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib"):
            if _os.path.isdir(d):
                _os.environ["LD_LIBRARY_PATH"] = d + _os.pathsep + _os.environ.get("LD_LIBRARY_PATH", "")
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER_WORKS": "1", "CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY"})
        cmake.build()

    def test(self):
        # R34: Actually run the compiled test binary
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_cryptokit")
            self.run(bin_path, env="conanrun")
