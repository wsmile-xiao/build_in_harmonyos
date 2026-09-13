#!/usr/bin/env python3
"""Conan recipe — geographiclib 2.7 (CMake).

GeographicLib — C++ geographic/geodesic library (MIT).
OHOS arm64 native: clang + CMake, no external deps (USE_BOOST=OFF).
适配修复: OHOS CMake 平台未定义 SOVERSION 时工具链接会带上构建树相对路径
(../src/libGeographicLib.so); 显式注入 CMAKE_SHARED_LINKER_FLAGS -Wl,-soname
保证 tools 的 DT_NEEDED 为 libGeographicLib.so, 安装后可运行。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class GeographiclibConan(ConanFile):
    name = "geographiclib"
    version = "2.7"
    description = "GeographicLib — 测地线/地理坐标 C++ 库 (MIT)"
    license = "MIT"
    homepage = "https://geographiclib.sourceforge.io/"
    url = "https://github.com/geographiclib/geographiclib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # geographiclib 无外部第三方依赖 (Boost 为可选且默认 OFF)
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["USE_BOOST"] = "OFF"
        # SOname 修复: OHOS 平台 CMake 未识别时工具 DT_NEEDED 会带构建树路径
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libGeographicLib.so"
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
        self.cpp_info.libs = ["GeographicLib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "GeographicLib")
        self.cpp_info.set_property("cmake_target_name", "GeographicLib::GeographicLib")
        # 工具目录 (GeodSolve/GeoConvert 等 CLI 工具, R38 由 commands.json 声明)
        self.cpp_info.bindirs = ["bin"]