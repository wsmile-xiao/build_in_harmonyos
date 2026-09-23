#!/usr/bin/env python3
"""Conan recipe — utfcpp20 0.3 (C++20 unicode conversion library).

utfcpp20 是 utfcpp 同作者的 C++20 Unicode 转换库：编译型小库
（src/core.cpp + src/utfcpp20.cpp，公共头 include/utfcpp20.hpp），
无第三方依赖。上游 CMake 无 install() 规则，且测试套件经
FetchContent 拉取 nemtrif/ftest（ftest 未在制品仓发布，构建环境
无网络），因此补丁将 tests 门控为 UTF20_BUILD_TESTS 选项（默认
OFF，生产构建零外部依赖）；上游套件在真机验证中单独运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Utfcpp20Conan(ConanFile):
    name = "utfcpp20"
    version = "0.3"
    description = "A C++ 20 library for working with Unicode strings"
    license = "Apache-2.0"
    homepage = "https://github.com/nemtrif/utfcpp20"
    url = "https://github.com/nemtrif/utfcpp20"
    topics = ("unicode", "utf-8", "utf-16", "cpp20")

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
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["UTF20_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # 上游无 install() 规则，从构建树收库产物
        copy(self, "*.a", self.build_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        if self.options.shared:
            copy(self, "*.so*", self.build_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "utfcpp20")
        self.cpp_info.set_property("cmake_target_name", "utfcpp20::utfcpp20")
        self.cpp_info.libs = ["utfcpp20"]
