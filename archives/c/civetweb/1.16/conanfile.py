#!/usr/bin/env python3
"""Conan recipe — civetweb 1.16 (CMake, C embedded HTTP server library).

civetweb 是一个嵌入式 C 语言 HTTP 服务器库，提供 C API（libcivetweb）。
上游用 CMake 构建，可选 OpenSSL/MbedTLS/Lua/zlib，基础构建（无 SSL）无第三方
依赖。本配方默认关闭可选功能（SSL/Lua/zlib/CGI/WebSocket），构建纯 C 库，
避免在 OHOS 平台上引入额外依赖链。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CivetwebConan(ConanFile):
    name = "civetweb"
    version = "1.16"
    description = "Embedded C/C++ web server (CivetWeb)"
    license = "MIT"
    homepage = "https://github.com/civetweb/civetweb"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "civetweb 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        # 源码根目录存在名为 build 的 bash 脚本文件，与 cmake_layout 默认
        # build_folder="build" 冲突（NotADirectoryError），改用独立构建目录名。
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # 上游 cmake_minimum_required(3.3.0)，CMake >= 4.1 已移除 <3.5 兼容，
        # 注入 policy 最低版本允许继续配置（CMake 官方建议，不改上游文件）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R26: 默认静态编译（非系统同名库，Conan 管理依赖链）
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.cache_variables["CIVETWEB_BUILD_TESTING"] = "OFF"
        # 关闭可选功能，减少依赖与平台风险
        tc.cache_variables["CIVETWEB_ENABLE_SSL"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_LUA"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_DUKTAPE"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_ZLIB"] = "OFF"
        tc.cache_variables["CIVETWEB_DISABLE_CGI"] = "ON"
        tc.cache_variables["CIVETWEB_ENABLE_WEBSOCKETS"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_CXX"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_SERVER_EXECUTABLE"] = "OFF"
        tc.cache_variables["CIVETWEB_ENABLE_ASAN"] = "OFF"
        tc.cache_variables["CIVETWEB_ALLOW_WARNINGS"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "civetweb")
        self.cpp_info.set_property("cmake_target_name", "civetweb::civetweb")
        self.cpp_info.libs = ["civetweb"]
        # dl 是系统库（非本包内部组件），必须用 system_libs 声明
        self.cpp_info.system_libs = ["dl"]
