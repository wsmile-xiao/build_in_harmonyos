#!/usr/bin/env python3
"""Conan recipe - libspatialaudio 0.4.1 (CMake, C++ spatial audio library)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibspatialaudioConan(ConanFile):
    name = "libspatialaudio"
    version = "0.4.1"
    description = "Open-source, real-time and cross-platform C++ library for spatial audio encoding, decoding and rendering"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/videolabs/libspatialaudio"
    url = ""
    topics = ("spatial-audio", "ambisonics", "binaural", "hoa", "renderer")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["HAVE_MIT_HRTF"] = True
        tc.variables["BUILD_TESTING"] = False
        # E383: OHOS 无 Platform/HarmonyOS.cmake 模块，CMAKE_SHARED_LIBRARY_SONAME_*_FLAG
        # 为空导致链接器不发射 SONAME（readelf -d 无 SONAME 条目）。与 E330 组合：
        # 保持 SONAME flag + CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON（HMDFS 路径不建版本化符号链接，
        # 生成未版本化 .so 且携带可重定位 ELF SONAME，下游 DT_NEEDED 不记录缓存绝对路径）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
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
        self.cpp_info.libs = ["spatialaudio"]
        # 静态库消费者需链接系统数学库（上游 CMake 对非 MSVC 使用 -lm）
        if not self.options.shared:
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "spatialaudio")
