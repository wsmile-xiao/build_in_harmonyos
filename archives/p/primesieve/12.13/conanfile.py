#!/usr/bin/env python3
"""Conan recipe for primesieve 12.13 (CMake build system).

Build system: CMake
Dependencies: Threads (system pthread, no third-party deps)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class PrimesieveConan(ConanFile):
    name = "primesieve"
    version = "12.13"
    description = "primesieve is a C/C++ library for generating primes using a highly optimized sieve of Eratosthenes"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kimwalisch/primesieve"
    url = "https://github.com/kimwalisch/primesieve"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        # 仅对 OHOS 生效，避免污染原生 Linux 构建（原生 Linux 不应覆写 SYSTEM_PROCESSOR）
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 构建静态库，禁用共享库（本项目仅支持静态库）
        tc.variables["BUILD_STATIC_LIBS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = False
        # 禁用命令行工具（仅需库文件）
        tc.variables["BUILD_PRIMESIEVE"] = False
        # 启用上游测试（test/ 目录，15 个测试，不依赖 Catch2）
        # 交叉编译时不构建测试目标（也无法运行）
        if not cross_building(self):
            tc.variables["BUILD_TESTS"] = True
        else:
            tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_MANPAGE"] = False
        # 启用多架构运行时分发（ARM SVE 优化）
        tc.variables["WITH_MULTIARCH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游测试（test/ 目录，15 个测试用例）
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "primesieve")
        self.cpp_info.set_property("cmake_target_name", "primesieve::primesieve")
        self.cpp_info.set_property("pkg_config_name", "primesieve")
        self.cpp_info.libs = ["primesieve"]
        # primesieve 依赖 pthread
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
