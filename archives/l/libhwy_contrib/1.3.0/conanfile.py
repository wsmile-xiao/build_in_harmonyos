#!/usr/bin/env python3
"""Conan recipe — libhwy_contrib 1.3.0（Google Highway contrib 目标库，鸿蒙 aarch64）.

构建上游 highway 1.3.0 的 hwy_contrib CMake 目标（vqsort 排序、image 图像、
thread_pool/topology 线程池等 contrib 实现），只安装编译产物 libhwy_contrib。
contrib 头文件与核心 libhwy 由依赖 highway/1.3.0.2 包提供，不重复打包头文件。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibhwyContribConan(ConanFile):
    name = "libhwy_contrib"
    version = "1.3.0"
    description = "Google Highway contrib 目标库（vqsort/image/thread_pool，依赖 highway 核心）"
    license = "Apache-2.0"
    homepage = "https://github.com/google/highway"
    url = "https://github.com/google/highway"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # 本包无源码补丁（conandata.yml 未声明 patches），声明以符合 G1 配方完整性
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)
        self.folders.build = "_build"
        self.folders.generators = "_build/generators"

    def requirements(self):
        # contrib 与核心同源同版本；核心头文件与 libhwy 链接由 highway 包传递
        self.requires("highway/1.3.0.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            # 跳过含链接步骤的编译器探测：部分 CI worker 的 lld 缺 libxml2
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        upstream_tests = self.options.with_upstream_tests
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON" if upstream_tests else "OFF"
        # 本包专投 hwy_contrib 目标，contrib 构建始终开启
        tc.variables["HWY_ENABLE_CONTRIB"] = "ON"
        tc.variables["HWY_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["HWY_ENABLE_INSTALL"] = "OFF"
        tc.variables["HWY_ENABLE_TESTS"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_FORCE_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # 上游自带 GTest 兼容运行器，避免 CI 沙箱 clone googletest
        tc.variables["HWY_TEST_STANDALONE"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_WARNINGS_ARE_ERRORS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        if self.settings.os == "OHOS" and not self.options.with_upstream_tests:
            # 只编 contrib 库目标，避免在 CI worker 上链接测试可执行文件
            cmake.build(target="hwy_contrib")
        else:
            cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            cmake.test()

    def package(self):
        copy(self, "libhwy_contrib.a", self.build_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libhwy_contrib.so*", self.build_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hwy_contrib"]
        # highway/1.3.0.2 配方未声明 cpp_info.includedirs，Conan 2 只给直接被测包
        # 补 ["include"] 默认值、传递依赖不补——CMakeDeps 链路上 highway 的 include
        # 为空。本包显式携带核心包 include 路径，保证 CMake 消费者拿到 hwy 头文件。
        hwy_dep = self.dependencies.get("highway")
        if hwy_dep and hwy_dep.package_folder:
            self.cpp_info.includedirs = [os.path.join(hwy_dep.package_folder, "include")]
        # 把核心包显式接进本包目标：消费者链 hwy::hwy_contrib 时自动获得
        # highway 的 libhwy 链接（Conan 2 不会自动传递包级依赖）。
        self.cpp_info.requires = ["highway::highway"]
        self.cpp_info.set_property("cmake_file_name", "hwy_contrib")
        self.cpp_info.set_property("cmake_target_name", "hwy::hwy_contrib")
        self.cpp_info.set_property("pkg_config_name", "libhwy-contrib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
