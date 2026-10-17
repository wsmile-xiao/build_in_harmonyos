#!/usr/bin/env python3
"""Conan recipe — libmysofa 1.3.5（ISC/BSD 类 C 库，鸿蒙 PC aarch64 移植）。

上游: https://github.com/hoene/libmysofa (tag v1.3.5)
依赖: zlib/1.3.1（SOFA 文件 gzip 解压路径 hdf/gunzip.c 需要；registry 已发布）
构建: CMake；静态 + 共享双库，导出头 mysofa.h + 构建期生成 mysofa_export.h
适配点: 仅测试代码两处平台修复（patches/0001 将 /tmp 输出改为工作目录 —
        鸿蒙 /tmp 只读；patches/0002 将 multithread watchdog 的
        pthread_cancel 改为标志位+join — OHOS musl 无 pthread_cancel 符号）。
上游测试: CUnit external/internal/multithread + 41 项 ctest，适配验证时全量
        运行（详见 MANIFEST.yml 与 test-report），配方构建库本体
        BUILD_TESTS=OFF（测试仅需 CUnit，由 test_package 消费侧验证）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibmysofaConan(ConanFile):
    name = "libmysofa"
    version = "1.3.5"
    description = "SOFA file reader for better HRTFs (AES SOFA format)"
    license = "ISC"
    homepage = "https://github.com/hoene/libmysofa"
    url = "https://github.com/hoene/libmysofa"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # hdf/gunzip.c 的 inflate 路径依赖 zlib（SOFA gzip 数据解压）
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 默认静态；系统无同名 libmysofa 冲突，但仍按仓库惯例静态打包
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # 测试由 test_package 与适配验证阶段覆盖，配方构建不引入 CUnit 依赖
        tc.variables["BUILD_TESTS"] = "OFF"
        if self.settings.os == "OHOS":
            # 上游 src/CMakeLists.txt 用 find_library(MATH m)；OHOS 交叉
            # sysroot 不在 CMake 默认搜索路径内（与 ci profile 仅注入
            # compiler_executables、未设 CMAKE_SYSROOT 对应），显式注入
            # sysroot 内 aarch64-linux-ohos 的 libm.a，避免 configure 报
            # "MATH...NOTFOUND"。arch 目录按 settings.arch 归一化。
            sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
            if sysroots:
                arch_dir = {
                    "armv8": "aarch64-linux-ohos",
                    "armv7": "arm-linux-ohos",
                    "x86_64": "x86_64-linux-ohos",
                }.get(str(self.settings.arch))
                if arch_dir:
                    libm = os.path.join(sysroots[-1], "usr", "lib", arch_dir, "libm.a")
                    if os.path.isfile(libm):
                        tc.variables["MATH"] = libm
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
        self.cpp_info.libs = ["mysofa"]