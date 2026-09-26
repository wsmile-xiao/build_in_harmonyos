#!/usr/bin/env python3
"""Conan recipe — cxxgraph 4.1.0 (CMake header-only graph library).

CXXGraph 是 header-only C++ 图算法库（ZigRazor/CXXGraph，MIT）。
library 本身只交付 include/ 头文件；上游测试 (test_exe, gtest 302 个
TEST/TEST_F 声明) 通过 CPM 拉取 googletest + zlib，CI worker 无法直连
github.com，故在 build() 阶段预下载本地源码，配合
patches/0001-use-local-gtest-zlib.patch 让 CPM 优先使用本地 SOURCE_DIR。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


class CxxgraphConan(ConanFile):
    name = "cxxgraph"
    version = "4.1.0"
    description = "Header-only C++ Graph Library (ZigRazor/CXXGraph)"
    license = "MIT"
    homepage = "https://github.com/ZigRazor/CXXGraph"
    url = ""  # CI fills this
    topics = ("graph", "algorithms", "header-only", "cpp17")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 OHOS 目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 上游 zlib 通过 CPM 以 cmake_minimum_required(<3.5) 配置，现代 CMake 已移除兼容层
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # gtest/zlib 本地源码目录（build() 中预下载，配合补丁让 CPM 使用本地 SOURCE_DIR）
        tc.cache_variables["CXXGRAPH_GTEST_SOURCE_DIR"] = os.path.join(self.build_folder, "gtest_src")
        tc.cache_variables["CXXGRAPH_ZLIB_SOURCE_DIR"] = os.path.join(self.build_folder, "zlib_src")
        # 顶层 CMakeLists 的 CPM.cmake 下载点：指定 CPM_SOURCE_CACHE 指向本地预下载
        tc.cache_variables["CPM_SOURCE_CACHE"] = os.path.join(self.build_folder, "cpm")
        # 启用上游测试、关闭 benchmark/examples
        tc.variables["TEST"] = True
        tc.variables["BENCHMARK"] = False
        tc.variables["EXAMPLES"] = False
        tc.generate()

    def build(self):
        # gtest 源码（上游 CPM 以 GIT_TAG origin/main 拉取，本地化以固定版本）
        gtest_data = self.conan_data.get("gtest_sources", {})
        if gtest_data:
            get(self, gtest_data["url"], sha256=gtest_data["sha256"],
                strip_root=True, destination=os.path.join(self.build_folder, "gtest_src"))
        # zlib 源码
        zlib_data = self.conan_data.get("zlib_sources", {})
        if zlib_data:
            get(self, zlib_data["url"], sha256=zlib_data["sha256"],
                strip_root=True, destination=os.path.join(self.build_folder, "zlib_src"))
        # CPM.cmake 引导脚本（configure 期顶层 CMakeLists 直连 GitHub 下载，本地化前置）
        cpm_data = self.conan_data.get("cpm_source", {})
        if cpm_data:
            cpm_dir = os.path.join(self.build_folder, "cpm", "cpm")
            os.makedirs(cpm_dir, exist_ok=True)
            download(self, cpm_data["url"], os.path.join(cpm_dir, "CPM.cmake"),
                     sha256=cpm_data["sha256"])

        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游 gtest 测试（301 个注册用例；302 个源码声明中 1 个在注释块内未实例化）
        if cross_building(self):
            self.output.info("cross-building: skip upstream test run")
            return
        # 测试数据文件（test_dot_*.dot / test_mtx*.mtx）按上游相对路径 ../../test 定位
        test_data_dir = os.path.normpath(os.path.join(self.build_folder, "..", "test"))
        os.makedirs(test_data_dir, exist_ok=True)
        src_test = os.path.join(self.source_folder, "test")
        for f in os.listdir(src_test):
            if f.endswith((".dot", ".mtx")):
                import shutil
                shutil.copy2(os.path.join(src_test, f), os.path.join(test_data_dir, f))
        self.run(f"cd {self.build_folder}/test && ./test_exe", env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CXXGraph")
        self.cpp_info.set_property("cmake_target_name", "CXXGraph::CXXGraph")
        self.cpp_info.libs = []