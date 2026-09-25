#!/usr/bin/env python3
"""Conan recipe — cpp-smtpclient-library 1.1.14 (CMake, C++14/17, OpenSSL).

- 上游库导出名为 smtpclient（CMake PROJECT_NAME），package_info 据此声明。
- 禁用 clang-tidy：上游 CMakeLists 的多行 --tidy 参数会生成语法损坏的
  build.make（missing separator），须用 cache_variables 而非 variables。
- 构建使用 -j1 规避 OHOS SELinux 对 make jobserver FIFO 的限制。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CppsmtpclientlibraryConan(ConanFile):
    name = "cpp-smtpclient-library"
    version = "1.1.14"
    description = "cpp-smtpclient-library 1.1.14"
    license = "MIT"
    homepage = "https://github.com/jeremydumais/CPP-SMTPClient-library"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 禁用 clang-tidy：上游 CMakeLists 的多行 clang-tidy 参数会生成
        # 语法损坏的 build.make（missing separator），且 clang-tidy 非构建必需。
        # 必须用 cache_variables（find_program 优先读 cache），variables 无效
        tc.cache_variables["CLANG_TIDY_EXE"] = "CLANG_TIDY_EXE-NOTFOUND"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # -j1: 避免 make jobserver 在 HMDFS 上 mkfifo 失败
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 实际构建产物为 libsmtpclient.so/.a（CMake 中 PROJECT_NAME=smtpclient）
        self.cpp_info.libs = ["smtpclient"]
        self.cpp_info.set_property("cmake_file_name", "smtpclient")
        self.cpp_info.set_property("cmake_target_name", "smtpclient::smtpclient")
