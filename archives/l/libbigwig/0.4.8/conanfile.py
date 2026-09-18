#!/usr/bin/env python3
"""Conan recipe — libbigwig 0.4.8 (CMake project).

libBigWig is a C library for reading and writing bigWig and bigBed files,
both local and (with libcurl) remote. It produces libBigWig.a / libBigWig.so
and depends on zlib plus optional libcurl.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class LibbigwigConan(ConanFile):
    name = "libbigwig"
    version = "0.4.8"
    description = "C library for reading and writing bigWig and bigBed files"
    license = "MIT"
    homepage = "https://github.com/dpryan79/libBigWig"
    url = "https://github.com/dpryan79/libBigWig"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_curl": [True, False],
    }
    default_options = {"shared": False, "fPIC": True, "with_curl": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        # zlib/1.3.1.1 是 PIC 静态包,与 curl/8.15.0 的传递依赖保持同一版本,
        # 避免依赖图中 zlib 版本冲突。
        self.requires("zlib/1.3.1.1")
        if self.options.with_curl:
            self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["WITH_CURL"] = "ON" if self.options.with_curl else "OFF"
        # 上游测试程序由 test_package 与独立验证流程负责,包构建内不编译。
        tc.variables["ENABLE_TESTING"] = "OFF"
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if self.options.fPIC else "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 PUBLIC_HEADER 安装到 include/libbigwig/ 子目录,上游消费者按
        # #include "bigWig.h" 使用,includedirs 须指向该子目录而非 include/
        self.cpp_info.includedirs = ["include/libbigwig"]
        self.cpp_info.libs = ["BigWig"]
        self.cpp_info.system_libs = ["m"]
        # bigWigIO.h 直接 #include <curl/curl.h>,静态库消费者须继承传递依赖
        # 的头文件与链接(CMakeDeps 按此声明链聚合)
        self.cpp_info.requires = ["zlib::zlib"]
        if self.options.with_curl:
            self.cpp_info.requires.append("curl::curl")
        self.cpp_info.set_property("cmake_file_name", "libbigwig")
        self.cpp_info.set_property("cmake_target_name", "libbigwig::libbigwig")
