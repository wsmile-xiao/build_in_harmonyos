#!/usr/bin/env python3
"""Conan recipe — fleur 0.3 (pure C bloom filter library, CMake build).

fleur 官方 CMakeLists.txt 无 install() 规则（TARGET_GROUP=production 时仅做
静态库 + fleurcli），故 package() 手工拷贝产物：
  - include/fleur.h        （公开 API 头）
  - lib/libfleur.a libfnv.a libmyutils.a
  - bin/fleurcli           （R38: CLI 工具，软件级 commands.json 对应声明）

构建通过 CMakeToolchain 设置 TARGET_GROUP=production（跳过 test/external）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class FleurConan(ConanFile):
    name = "fleur"
    version = "0.3"
    description = "Fleur - a C bloom filter library compatible with DCSO's Go/Python implementations"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hashlookup/fleur"
    url = "https://github.com/hashlookup/fleur"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 系统同名库默认静态；fleur 上游 CMake 显式 STATIC，BUILD_SHARED_LIBS 仅为一致
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 只构建生产目标（库 + fleurcli），不构建 test/external(Unity)
        tc.variables["TARGET_GROUP"] = "production"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游无 install() 规则，手工拷贝产物与公开头
        copy(self, "fleur.h", src=os.path.join(self.source_folder, "fleur"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "fleurcli", src=os.path.join(self.build_folder, "fleurcli"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # fleur.a 依赖 fnv/myutils 符号与 libm
        self.cpp_info.libs = ["fleur", "fnv", "myutils"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]