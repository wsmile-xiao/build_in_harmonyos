#!/usr/bin/env python3
"""Conan recipe — SZ3 3.3.2 (header-only C++17 error-bounded lossy compressor).

上游：https://github.com/szcompressor/SZ3 (tag v3.3.2)
形态：INTERFACE header-only 库 + 可选 CLI 工具（BUILD_SZ3_BINARY=ON，上游默认）
依赖：zstd（无损失后级，经根 CMakeLists 的 pkg_search_module(libzstd) 发现）
测试：上游 tools/test/（gtest，BUILD_TESTING=ON 注册 3 个可执行/7 个原子用例），
      本配方 build() 内真实执行（cmake.test()）。

平台注记（HarmonyOS PC / aarch64）：
- OpenMP / GSL 为上游可选依赖，本配方显式关闭（CMAKE_DISABLE_FIND_PACKAGE_*）
  以保证交叉构建确定性；不影响功能（串行语义）。
- zstd 经 conan 制品（静态）提供，PkgConfigDeps 生成 libzstd.pc 注入
  PKG_CONFIG_PATH，命中上游 pkg_search_module 分支，不编译上游捆包的
  tools/zstd（避免捎带第三方源码构建）。
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class SzConan(ConanFile):
    name = "sz"
    version = "3.3.2"
    description = "SZ3: modular error-bounded lossy compressor for scientific data (header-only C++17)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/szcompressor/SZ3"
    url = "https://github.com/szcompressor/SZ3"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SZ3 的 INTERFACE target 以 pkg-config 形式链接 zstd（无损失后级）。
        # 上游捆包 tools/zstd 分支仅在找不到 libzstd.pc 时启用——本配方经
        # PkgConfigDeps 命中 conan 制品，不构建捆包副本（R36/R26 口径）。
        self.requires("zstd/1.5.7.1")

    def build_requirements(self):
        # 上游 tools/test/ 为 gtest 套件（find_package(GTest) + GTest::gtest_main）
        self.test_requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # 上游测试：BUILD_TESTING=ON 注册 tools/test/modules/ 3 个 gtest 可执行
        tc.variables["BUILD_TESTING"] = "ON"
        # 上游默认即 OFF 的重依赖子项目，显式声明以固定构建面
        tc.variables["BUILD_H5Z_FILTER"] = "OFF"      # 需 HDF5
        tc.variables["BUILD_MDZ"] = "OFF"
        tc.variables["BUILD_PARAVIEW_PLUGIN"] = "OFF"
        # 可选依赖确定性：OHOS clang 的 OpenMP 运行库不可依赖，GSL 未适配，
        # 两者均为上游可选增强（找不到即跳过），显式禁用保证 CI 可复现
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_GSL"] = "ON"
        # 走 conan 制品的 libzstd.pc（见 requirements()），不编译捆包 zstd
        tc.variables["SZ3_USE_BUNDLED_ZSTD"] = "OFF"
        tc.generate()
        # 生成 libzstd.pc 供根 CMakeLists 的 pkg_search_module(libzstd) 命中
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # conan 不会自动把 generators_folder 注入 PKG_CONFIG_PATH；
        # 根 CMakeLists 的 pkg_search_module(libzstd) 在 configure 期执行查找
        penv = Environment()
        penv.define_path("PKG_CONFIG_PATH", self.generators_folder)
        with penv.vars(self).apply():
            cmake.configure()
            cmake.build()
        # 上游测试真实执行（BUILD_TESTING=ON → ctest；gtest_discover_tests PRE_TEST）
        if can_run(self):
            tenv = Environment()
            tenv.define("CTEST_OUTPUT_ON_FAILURE", "1")
            with tenv.vars(self).apply():
                cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # INTERFACE header-only 库：无 libs，仅头文件 + CLI 工具
        self.cpp_info.set_property("cmake_file_name", "SZ3")
        self.cpp_info.set_property("cmake_target_name", "SZ3::SZ3")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # INTERFACE target 传递链接 zstd（PkgConfig::ZSTD），conan 消费者
        # 经 cpp_info.requires 获得等价传递语义
        self.cpp_info.requires.append("zstd::zstd")
