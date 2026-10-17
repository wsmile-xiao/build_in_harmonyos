#!/usr/bin/env python3
"""Conan recipe for keystone 0.9.2 (CMake build system).

Build system: CMake (vendored LLVM under llvm/)
Dependencies: none (LLVM is vendored, no external deps)
Outputs: libkeystone (library) + kstool (executable)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KeystoneConan(ConanFile):
    name = "keystone"
    version = "0.9.2"
    description = "Lightweight multi-platform, multi-architecture assembler framework"
    license = "GPL-2.0-only"
    homepage = "https://github.com/keystone-engine/keystone"
    url = ""

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build kstool executable (not libs-only)
        tc.variables["BUILD_LIBS_ONLY"] = False
        # Build all supported architectures
        tc.variables["LLVM_TARGETS_TO_BUILD"] = "all"
        # Old vendored LLVM uses common symbols (tentative definitions) which
        # cause duplicate-symbol link errors on clang 15+; -fcommon lets the
        # linker merge them (see project lesson learned for old C/C++ projects).
        tc.extra_cxxflags.append("-fcommon")
        tc.extra_cflags.append("-fcommon")
        tc.generate()
        # NOTE: CMAKE_POLICY_VERSION_MINIMUM 不能放进 tc.variables —— 那会写入
        # conan_toolchain.cmake 作为普通 set()，而 toolchain 文件在 project() 时
        # 才加载，晚于源码 CMakeLists.txt:4 的 cmake_minimum_required(VERSION 2.8.7)。
        # CMake 3.27+ 在解析 cmake_minimum_required 时若看不到该变量就会报
        # "Compatibility with CMake < 3.5 has been removed"。必须用 -D 命令行
        # cache 变量传递（见 build() 中的 cmake.configure(variables=...)）。

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM 作为 -D 命令行 cache 变量传递，
        # 在 cmake_minimum_required() 解析前就被 CMake 读到（见 generate() 注释）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["keystone"]
        self.cpp_info.includedirs = ["include"]
        # C++ standard library needed when linking static libkeystone.a
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++"]
