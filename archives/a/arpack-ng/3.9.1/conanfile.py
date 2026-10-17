#!/usr/bin/env python3
"""Conan recipe — arpack-ng 3.9.1 (cmake, HarmonyOS PC / os=OHOS arch=armv8)

arpack-ng 是 Fortran 特征值求解库，依赖 BLAS/LAPACK。
本 recipe 使用 flang-ohos tool_requires 提供 Fortran 编译器，
CMake 构建系统，启用 ICB (ISO C Binding) 提供 C 接口。

依赖:
  - openblas/0.3.34 (BLAS + LAPACK 实现)
  - lapack/3.12.1 (LAPACK 参考实现, 与 openblas 互补)
  - tool_requires flang-ohos/20.1.0 (LLVM Flang Fortran 编译器)
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.errors import ConanInvalidConfiguration


class ArpackNgConan(ConanFile):
    name = "arpack-ng"
    version = "3.9.1"
    description = "Collection of Fortran77 subroutines designed to solve large scale eigenvalue problems"
    license = "BSD-3-Clause"
    homepage = "https://github.com/opencollab/arpack-ng"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "ICB": [True, False]}
    default_options = {"shared": False, "ICB": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须用 in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"arpack-ng 仅支持 os=Linux 或 os=OHOS, 当前 os={self.settings.os}")

    def requirements(self):
        self.requires("openblas/0.3.34")
        self.requires("lapack/3.12.1")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # 获取 flang-ohos 包路径
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        rt = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")

        # 设置 LD_LIBRARY_PATH 以运行 flang
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)

        # 清 HiShell 污染的构建 env
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(k, None)

        # OHOS 平台 make jobserver FIFO 创建失败, 限制单线程构建
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        # OHOS 平台 make jobserver FIFO 创建失败 (Operation not permitted)
        # 限制并行编译为 1 个 job 以避免 jobserver 问题
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        # 限制并行构建 (OHOS 平台 make jobserver FIFO 创建失败)
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        tc = CMakeToolchain(self)
        # 禁用 source-side preset (E225)
        tc.user_presets_path = False
        # 设置 Fortran 编译器
        tc.variables["CMAKE_Fortran_COMPILER"] = fc
        # 静态/动态库
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # 启用 ICB (ISO C Binding) 提供 C 接口
        tc.variables["ICB"] = self.options.ICB
        tc.variables["EXAMPLES"] = False
        tc.variables["TESTS"] = False
        tc.variables["MPI"] = False
        # OHOS 平台需要设置 CMAKE_SYSTEM_NAME 和跳过链接测试
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            # 跳过 CMake 编译器检查 (OHOS 平台 clang 在 conan cache 中 try-compile 异常)
            tc.variables["CMAKE_C_COMPILER_FORCED"] = True
            tc.variables["CMAKE_CXX_COMPILER_FORCED"] = True
            # 跳过 FindThreads 检查 (OHOS 平台 try-compile 在 conan cache 中异常)
            tc.variables["CMAKE_THREAD_LIBS_INIT"] = "-lpthread"
            tc.variables["CMAKE_HAVE_THREADS_LIBRARY"] = "1"
            tc.variables["CMAKE_USE_PTHREADS_INIT"] = "1"
            # sysroot 路径: OHOS SDK 的 sysroot
            sysroot = sdk_llvm_lib.replace("/llvm/lib", "/sysroot") if sdk_llvm_lib else ""
            llvm_rt_dir = os.path.join(sdk_llvm_lib, "clang", "15.0.4", "lib", "aarch64-linux-ohos") if sdk_llvm_lib else ""
            # 编译器标志: sysroot (C/CXX 编译需要找到系统头文件)
            if sysroot:
                tc.extra_cflags.append(f"--sysroot={sysroot}")
                tc.extra_cxxflags.append(f"--sysroot={sysroot}")
            # 链接器标志: sysroot + LLVM runtime + Fortran runtime
            link_flags = []
            if sysroot:
                link_flags.append(f"--sysroot={sysroot}")
            if sdk_llvm_lib:
                link_flags.append(f"-L{sdk_llvm_lib}/aarch64-linux-ohos")
            if llvm_rt_dir:
                link_flags.append(f"-L{llvm_rt_dir}")
            link_flags.append(rt)
            link_flags.append("-lm")
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(link_flags)
            tc.variables["CMAKE_Fortran_LINK_FLAGS"] = " ".join(link_flags)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["arpack"]
        self.cpp_info.includedirs = ["include/arpack"]
        self.cpp_info.set_property("pkg_config_name", "arpack")
        self.cpp_info.system_libs = ["m"]
