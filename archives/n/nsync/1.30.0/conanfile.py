#!/usr/bin/env python3
"""Conan recipe — nsync 1.30.0 (CMake)"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class NsyncConan(ConanFile):
    name = "nsync"
    version = "1.30.0"
    description = "nsync is a C library that exports various synchronization primitives, such as mutexes and condition variables"
    license = "Apache-2.0"
    homepage = "https://github.com/google/nsync"
    url = "https://github.com/google/nsync"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        # 源码解到 src/ 子目录：nsync 顶层有 bazel 的 BUILD 文件，若与源码同层，
        # 在大小写不敏感的 CI worker 文件系统上会与 cmake_layout 的 build/ 目录冲突
        # （makedirs build/Release → ENOTDIR）。隔离到 src/ 规避。
        cmake_layout(self, src_folder="src")

    def generate(self):
        import os
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # host/build profile 同为 os=OHOS 时 conan 判定非交叉编译、不写 CMAKE_SYSTEM_NAME，
        # cmake 退回宿主 Linux → nsync 走 platform/linux futex 分支，引入 musl 无的 <linux/futex.h>。
        # 显式声明 OHOS，令 nsync 落入通用 POSIX 分支（pthread mutex/cond 信号量，musl 兼容）。
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # 交叉模式下 cmake 对 OHOS 探测不出 CMAKE_C_COMPILER_ID → nsync 不追加 platform/clang
            # 编译器头目录（atomic.h/compiler.h）。此处按 clang 显式补回该目录。
            tc.extra_cflags.append("-I" + os.path.join(self.source_folder, "platform", "clang"))
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 不编上游测试（只发布库）
        tc.variables["NSYNC_ENABLE_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=self.package_folder + "/licenses")
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # nsync = C API; nsync_cpp = 同源用 C++ 编译的变体
        self.cpp_info.libs = ["nsync_cpp", "nsync"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
