#!/usr/bin/env python3
"""Conan recipe — ceres 2.2.0 (Ceres Solver, HarmonyOS PC 适配)。

上游：https://github.com/ceres-solver/ceres-solver  tag 2.2.0
依赖：仅 Eigen3（头文件库，制品仓已有 eigen/3.4.1）。
      glog / gflags / SuiteSparse / LAPACK / CUDA 全部关闭：
      · MINIGLOG=ON  → 用上游自带的极简 glog 替身，无需 glog 包；
      · GFLAGS=OFF   → 示例/工具用的 gflags 不需要；
      · SUITESPARSE=OFF + EIGENSPARSE=ON → 稀疏求解走 Eigen，无需 SuiteSparse/LAPACK。
产物：静态库 libceres.a（BUILD_SHARED_LIBS=OFF；shared=True 时产出 .so）。
"""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class CeresConan(ConanFile):
    name = "ceres"
    version = "2.2.0"
    package_type = "library"
    description = ("Ceres Solver — 大规模非线性最小二乘与优化库 "
                   "(large scale nonlinear least squares / optimization)")
    license = "BSD-3-Clause"
    url = "https://github.com/ceres-solver/ceres-solver"
    homepage = "http://ceres-solver.org"
    topics = ("optimization", "least-squares", "nonlinear", "solver", "numerical")

    # 关键：**不要**把源码拷进构建目录（no_copy_source）。
    # 上游 ceres 源码树顶层有一个 `BUILD` 文件（Bazel 用），而 cmake_layout 的构建目录叫 `build/`。
    # 官方 CI 的存储是 HMDFS（鸿蒙分布式文件系统，**大小写不敏感**，见知识库 E416），
    # 于是先被拷贝进构建目录的文件 `BUILD` 占掉了 `build` 这个名字，Conan 随后
    # os.makedirs('.../b/build/Release') 直接 NotADirectoryError
    # （CI 构建 #63833、elapsedTime 98s、进度 0% 实测）。
    # 本地 ext4 大小写敏感，所以本机复现不出来——必须按 CI 的文件系统语义修。
    no_copy_source = True

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # 保留少量上游开关，便于下游按需启用（默认与“最小依赖”口径一致）
        "with_glog": [True, False],
        "with_gflags": [True, False],
        "with_suitesparse": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        # 默认 MINIGLOG（= with_glog False）：Ceres 的公共头文件会 `#include "glog/logging.h"`，
        # MINIGLOG 模式下该 include 由上游自带的 miniglog 头满足——上游把
        # `include/ceres/internal/miniglog` 作为 **INSTALL_INTERFACE PUBLIC** 导出
        # （见 internal/ceres/CMakeLists.txt 的 target_include_directories(ceres BEFORE PUBLIC ...)），
        # 因此只要配方在 cpp_info.includedirs 里**镜像**这个目录，消费者即可正常编译，
        # 且整条依赖链只剩 Eigen。开启 with_glog 时改用真实 glog（glog/0.7.1 + gflags 已有配方），
        # 但要绕开上游 FindGlog 对 Conan 生成配置的识别问题（见 REPORT-36）。
        "with_glog": False,
        "with_gflags": False,
        "with_suitesparse": False,
    }

    def requirements(self):
        # 头文件库；Ceres 2.2 的 CMake 请求 find_package(Eigen3 3.3 REQUIRED)
        self.requires("eigen/3.4.1")
        if self.options.with_glog:
            self.requires("glog/0.7.1")
        if self.options.with_gflags:
            self.requires("gflags/2.3.1")
        if self.options.with_suitesparse:
            self.requires("suitesparse/7.8.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        # 依赖裁剪：只留 Eigen
        tc.variables["MINIGLOG"] = not bool(self.options.with_glog)
        tc.variables["GFLAGS"] = bool(self.options.with_gflags)
        tc.variables["SUITESPARSE"] = bool(self.options.with_suitesparse)
        tc.variables["LAPACK"] = False
        tc.variables["USE_CUDA"] = False
        tc.variables["EIGENSPARSE"] = True
        tc.variables["SCHUR_SPECIALIZATIONS"] = True
        # 不构建上游测试/示例/基准（上游 909 个 gtest 用例另在 MANIFEST 中如实申报）
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False
        tc.variables["PROVIDE_UNINSTALL_TARGET"] = False
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if not self.options.shared:
            # 上游无条件同时安装静态/共享（视 BUILD_SHARED_LIBS），剔除未请求的变体
            import glob
            for pat in ("libceres.so*", "libceres.*.dylib", "ceres.dll", "libceres.dll"):
                for f in glob.glob(os.path.join(self.package_folder, "lib", pat)):
                    os.remove(f)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Ceres")
        self.cpp_info.set_property("cmake_target_name", "Ceres::ceres")
        self.cpp_info.set_property("pkg_config_name", "ceres")
        self.cpp_info.libs = ["ceres"]
        # MINIGLOG 模式：镜像上游的 INSTALL_INTERFACE PUBLIC 目录，
        # 否则消费者编译 ceres 公共头文件时 `#include "glog/logging.h"` 失败
        # （实测 fatal error: 'glog/logging.h' file not found）。
        if not self.options.with_glog:
            self.cpp_info.includedirs = ["include", "include/ceres/internal/miniglog"]
        # 传递依赖必须显式声明，否则消费者拿到 ceres 头文件后找不到 Eigen/glog 的头
        reqs = ["eigen::eigen"]
        if self.options.with_glog:
            reqs.append("glog::glog")
        if self.options.with_gflags:
            reqs.append("gflags::gflags")
        self.cpp_info.requires = reqs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
