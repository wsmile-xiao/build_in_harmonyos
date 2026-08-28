#!/usr/bin/env python3
"""Conan recipe — clblas 2.12 (CMake, OpenCL)

clBLAS is an OpenCL BLAS library (https://github.com/clMathLibraries/clBLAS).
This recipe builds the OpenCL API library (libclBLAS) natively on HarmonyOS PC
(os=OHOS, arch=armv8).

Build facts:
  - CMakeLists.txt lives under src/ (top-level dir has no CMakeLists), so
    cmake.configure() must point source_dir at src/.
  - The library runtime (BUILD_RUNTIME) only needs OpenCL: headers from the
    opencl-headers package, libOpenCL.so from opencl-icd-loader.
  - BUILD_TEST requires google test + Boost + ACML/NETLIB BLAS (and a Fortran
    compiler on Linux/OHOS for the netlib reference); none of these exist in
    the OHOS toolchain/SDK, so the test suite is disabled here and the
    upstream test result is recorded honestly in manifest.yaml.
  - BUILD_KTEST / BUILD_CLIENT require Boost -> OFF. BUILD_SAMPLE /
    BUILD_PERFORMANCE are auxiliary -> OFF.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ClblasConan(ConanFile):
    name = "clblas"
    version = "2.12"
    description = "OpenCL BLAS library"
    license = "Apache-2.0"
    homepage = "https://github.com/clMathLibraries/clBLAS"
    url = "https://github.com/clMathLibraries/clBLAS"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # OpenCL headers (header-only) + ICD loader (libOpenCL.so)
        self.requires("opencl-headers/2026.05.29")
        self.requires("opencl-icd-loader/v2024.05.08")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 所有 BUILD_* 选项必须走 cache_variables（作为 -D 传入 CMake）：
        # clblas 的 option() 以 cache 变量优先，tc.variables 的普通 set()
        # 不生效（曾因 BUILD_TEST 默认 ON 触发 Fortran 编译器探测失败）
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 只构建核心运行库（libclBLAS）；测试/客户端/ktest 依赖
        # Boost + ACML/NETLIB BLAS + Fortran，OHOS 工具链均缺失 -> OFF
        tc.cache_variables["BUILD_RUNTIME"] = "ON"
        tc.cache_variables["BUILD_TEST"] = "OFF"
        tc.cache_variables["BUILD_CLIENT"] = "OFF"
        tc.cache_variables["BUILD_KTEST"] = "OFF"
        tc.cache_variables["BUILD_SAMPLE"] = "OFF"
        tc.cache_variables["BUILD_PERFORMANCE"] = "OFF"
        # clblas 的自定义 FindOpenCL.cmake 查找 OPENCL_INCLUDE_DIRS /
        # OPENCL_LIBRARIES；直接从 conan 依赖注入（clblast 先例同款）
        headers = self.dependencies["opencl-headers"].package_folder
        loader = self.dependencies["opencl-icd-loader"].package_folder
        tc.variables["OPENCL_INCLUDE_DIRS"] = os.path.join(headers, "include")
        tc.variables["OPENCL_LIBRARIES"] = os.path.join(loader, "lib", "libOpenCL.so")
        # 接受老版 cmake_minimum_required（opencl-icd-loader 同款）：
        # 必须走 cache_variables 才会作为 -D 传给 CMake 命令行
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 主配置的 -D 不会传给 tplgen（ExternalProject 子构建，其 CMakeLists
        # 同样 cmake_minimum_required < 3.5）；CMake 3.27+ 支持同名环境变量，
        # 子进程继承环境 -> tplgen 子配置不再报策略版本错误
        env = Environment()
        env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        env.vars(self).save_script("conanbuild_policy")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # CMakeLists.txt 在 src/ 子目录，用 build_script_folder 指向
        # （Conan 2 的 CMake.configure 无 source_dir 参数）
        cmake.configure(build_script_folder="src")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # clBLAS 的 CMake 把库安装到 lib64/import/（非 conan 约定的 lib/）；
        # 复制到 lib/ 供 consumers 的 cpp_info.libdirs 默认查找（clblast 同款）
        import_dir = os.path.join(self.package_folder, "lib64", "import")
        if os.path.isdir(import_dir):
            copy(self, "*", src=import_dir,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["clBLAS"]
