#!/usr/bin/env python3
"""Conan recipe — log4cplus 2.1.2（C++ 日志库，鸿蒙 aarch64）.

log4cplus 是一个线程安全、灵活、细粒度日志管理 C++ 库，
API 借鉴 Java log4j。
构建系统：CMake
平台：OHOS aarch64 / Linux / macOS / Windows
依赖：Threads（pthreads）
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Log4cplusConan(ConanFile):
    name = "log4cplus"
    version = "2.1.2"
    description = "log4cplus — 简单易用的 C++ 日志 API，线程安全、灵活、细粒度日志管理"
    license = "Apache-2.0 AND BSD-2-Clause"
    homepage = "https://github.com/log4cplus/log4cplus"
    url = "https://github.com/log4cplus/log4cplus"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # log4cplus 零外部依赖（仅系统 pthreads）

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 将 Conan 的 shared/fPIC 选项传递给 CMake
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        # OHOS/HarmonyOS 是 CMake 未知平台，UNIX 变量默认为 FALSE，
        # 导致 src/CMakeLists.txt 不编译 socket-unix.cxx（内含全部 socket helper
        # 实现：getHostname/openSocket/closeSocket 等），库缺失这些符号。
        # 显式设置 UNIX=TRUE 使 socket-unix.cxx 编入库。
        if self.settings.os in ("OHOS", "Linux"):
            tc.variables["UNIX"] = "TRUE"
        # 禁用 logging server（仅构建库本身）
        tc.variables["LOG4CPLUS_BUILD_LOGGINGSERVER"] = "OFF"
        # 启用上游测试（规则 5：LOG4CPLUS_BUILD_TESTING=ON 构建 tests/ 套件，
        # build() 中运行 ctest 记录真实通过率）
        tc.variables["LOG4CPLUS_BUILD_TESTING"] = "ON"
        # 禁用单线程模式（OHOS 支持多线程）
        tc.variables["LOG4CPLUS_SINGLE_THREADED"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 规则 5：实际运行上游测试（16 套件 / 206 断言，ctest）
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # log4cplus 的 CMake 构建系统根据 BUILD_SHARED_LIBS 决定库名：
        #   共享库 -> liblog4cplus.so  (库名 log4cplus)
        #   静态库 -> liblog4cplusS.a  (库名 log4cplusS)
        if self.options.shared:
            self.cpp_info.libs = ["log4cplus"]
        else:
            self.cpp_info.libs = ["log4cplusS"]
        # pthread 和 dl 仅 Linux/OHOS 需要，macOS 上为系统内置无需显式链接
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "log4cplus")
        self.cpp_info.set_property("cmake_target_name", "log4cplus::log4cplus")
        self.cpp_info.set_property("pkg_config_name", "log4cplus")
