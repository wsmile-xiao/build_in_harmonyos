#!/usr/bin/env python3
"""Conan test_package — cmor 3.15.2 消费者测试。

同 cpp_info.requires / headers=True 传递在 CMakeDeps 中对仅可见依赖
不填充 include 路径（已实证：udunits_INCLUDE_DIRS 经 cmor-only 依赖时为空）。
cmor 的公共头文件（cmor_func_def.h）直接 #include <udunits2.h>、
<json-c/json.h>、<netcdf.h>、<uuid/uuid.h>，消费者工程必须能直接包含
这些依赖头，所以 test_package 显式声明全部硬依赖。

运行期：netcdf → hdf5 的 C++ 绑定库（libhdf5_hl_cpp/libhdf5_cpp）需要
libc++_shared.so；它位于 OHOS NDK clang lib 目录，不在 conanrun 环境
LD_LIBRARY_PATH 中。test() 运行时补上（与主包 _runtime_env 同源）。

L0d 门禁要求 test() 通过 self.run() 直接执行测试二进制（而非仅
cmake.test()），故这里显式运行 test_cmor。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class CmorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cmor 公共头文件直接 include 依赖头，消费者编译必需。
        self.requires("netcdf/4.9.3", headers=True)
        self.requires("udunits/2.2.28.1", headers=True)
        self.requires("json-c/0.17", headers=True)
        self.requires("uuid/2.40.1", headers=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # netcdf → hdf5 C++ 绑定库（libhdf5_hl_cpp/libhdf5_cpp）运行需要
        # libc++_shared.so，位于 OHOS NDK clang lib 目录；conanrun 环境
        # 不含该目录，需在运行前补充到 LD_LIBRARY_PATH。
        env = Environment()
        libcxx_dirs = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/"
            "lib/aarch64-linux-ohos"))
        for d in libcxx_dirs:
            if os.path.isdir(d):
                env.prepend_path("LD_LIBRARY_PATH", d)
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_cmor"),
                env="conanrun",
            )