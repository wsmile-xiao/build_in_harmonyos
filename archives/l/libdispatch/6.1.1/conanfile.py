#!/usr/bin/env python3
"""Conan recipe for libdispatch 6.1.1 — CMake project.

libdispatch (swift-corelibs-libdispatch) provides Grand Central Dispatch
support for concurrent code execution on HarmonyOS PC (aarch64).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibdispatchConan(ConanFile):
    name = "libdispatch"
    version = "6.1.1"
    description = "Comprehensive support for concurrent code execution"
    license = "Apache-2.0"
    homepage = "https://github.com/apple/swift-corelibs-libdispatch"
    url = "https://github.com/apple/swift-corelibs-libdispatch"

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
        # get()/unzip() with strip_root=True fails on upstream PATCHES file
        # (IsADirectoryError on OHOS).  Use curl + tar directly to avoid the bug.
        # CI may inject a mirror list via E017, so support both string and list.
        url = self.conan_data["sources"]["url"]
        if isinstance(url, list):
            url = url[0]  # E017: take first mirror
        filename = self.conan_data["sources"].get("filename", "archive.tar.gz")
        # Try primary URL; fall back to direct GitHub URL if mirror returns 403.
        ret = self.run(f"curl -fsSL '{url}' -o {filename}", ignore_errors=True)
        if ret != 0:
            fallback = "https://github.com/apple/swift-corelibs-libdispatch/archive/refs/tags/swift-6.1.1-RELEASE.tar.gz"
            self.run(f"curl -fsSL '{fallback}' -o {filename}")
        self.run(f"tar xzf {filename} --strip-components=1 --exclude=PATCHES")
        self.run(f"rm -f {filename}")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_SWIFT"] = "OFF"
        tc.variables["ENABLE_DTRACE"] = "OFF"
        tc.variables["CMAKE_C_FLAGS"] = "-D__OHOS__ -DHAVE_DECL___PROGNAME=1 -fblocks"
        tc.variables["CMAKE_CXX_FLAGS"] = "-D__OHOS__ -DHAVE_DECL___PROGNAME=1 -fblocks"
        # R8: 不在补丁中硬编码平台条件宏；OHOS musl libc 提供 __progname
        # (与 Android 相同)，通过 C 编译器宏注入检测结果。
        tc.variables["HAVE_DECL___PROGNAME"] = "1"
        # CI 环境 lld 缺 libxml2.so.16，所有链接测试均崩溃。
        # 跳过编译器测试 + 注入 pthread 检测结果，避免 CMake 尝试链接。
        tc.variables["CMAKE_C_COMPILER_WORKS"] = "ON"
        tc.variables["CMAKE_CXX_COMPILER_WORKS"] = "ON"
        tc.variables["CMAKE_HAVE_LIBC_PTHREAD"] = "1"
        tc.variables["CMAKE_THREAD_LIBS_INIT"] = "-lpthread"
        tc.variables["Threads_FOUND"] = "TRUE"
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
        self.cpp_info.libs = ["dispatch", "BlocksRuntime"]
