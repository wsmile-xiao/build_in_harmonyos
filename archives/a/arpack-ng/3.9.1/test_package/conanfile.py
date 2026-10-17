#!/usr/bin/env python3
"""Conan test_package — arpack-ng 3.9.1

Tests the ICB C API (dsaupd_c / dseupd_c) by solving a simple
symmetric eigenvalue problem and verifying the results.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ArpackNgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeDeps auto-generates; CMakeToolchain is manually created in generate()
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # flang-ohos provides the Fortran runtime (libFortranRuntime.a)
        # needed to link libarpack.a which contains Fortran code
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS 平台 make jobserver FIFO 创建失败, 限制单线程构建
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # OHOS sysroot for CRT and system libraries
        ohos_sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["CMAKE_VERBOSE_MAKEFILE"] = True
        # 跳过 CMake 编译器检查 (OHOS 平台 clang 在 conan cache 中 try-compile 异常)
        tc.variables["CMAKE_C_COMPILER_FORCED"] = True
        tc.variables["CMAKE_CXX_COMPILER_FORCED"] = True
        # 编译器标志: sysroot (C 编译需要找到系统头文件)
        tc.extra_cflags.append(f"--sysroot={ohos_sysroot}")
        # Link the Fortran runtime from flang-ohos
        flang_lib = self.dependencies.build["flang-ohos"].cpp_info.libdirs[0]
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"--sysroot={ohos_sysroot} "
            f"-L{flang_lib} -lFortranRuntime -lFortranDecimal "
            f"-L{llvm_lib}/aarch64-linux-ohos "
            f"-L{llvm_lib}/clang/15.0.4/lib/aarch64-linux-ohos"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (R34: 实质调用 arpack-ng API)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_arpack")
        self.run(test_bin, env="conanrun")
