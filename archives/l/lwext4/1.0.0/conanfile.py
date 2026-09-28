#!/usr/bin/env python3
"""Conan recipe — lwext4 1.0.0 (CMake 构建).

lwext4：面向 MCU 的 ext2/3/4 文件系统库（C，静态库）。
- 上游 CMakeLists 要求 cmake_minimum_required(VERSION 2.8)（过旧，cmake 4.x 拒绝）
  → generate() 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5。
- LIB_ONLY=TRUE 只构建库，不构建 fs_test 可执行文件（/usr/bin 安装规则仅限
  fs_test，库本身无 install 规则，package() 手动复制 lib 与头文件）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class Lwext4Conan(ConanFile):
    name = "lwext4"
    version = "1.0.0"
    description = "lwext4 1.0.0 - ext2/3/4 filesystem library for microcontrollers"
    license = "GPL-2.0"
    homepage = "https://github.com/gkostka/lwext4"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(2.8) 在 cmake>=3.5 不再兼容（cmake 4.1 直接拒绝）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 只构建库目标（lwext4 / blockdev），跳过 fs_test 示例
        tc.variables["LIB_ONLY"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游无库安装规则，手动复制静态库与公共头文件
        copy(self, "liblwext4.a",
             src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "lib"))
        # 公共头文件递归复制（include/generated/ext4_config.h 由构建期生成，
        # 位于 build_folder/include/generated/，ext4_config.h 会 #include 它）
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "generated/*.h",
             src=os.path.join(self.build_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["lwext4"]
