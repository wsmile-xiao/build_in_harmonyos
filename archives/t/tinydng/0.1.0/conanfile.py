#!/usr/bin/env python3
"""Conan recipe — tinydng 0.1.0 (header-only C++11 DNG loader/writer).

tinydng 是单头文件形式的 DNG/TIFF 加载器与写入器（tiny_dng_loader.h /
tiny_dng_writer.h），无任何外部依赖。ZIP 压缩瓦片支持需要同时打包 miniz
（头 + 实现），供消费方按需启用 TINY_DNG_LOADER_ENABLE_ZIP。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.layout import basic_layout


class TinydngConan(ConanFile):
    name = "tinydng"
    version = "0.1.0"
    description = "Tiny but portable DNG (Digital Negative) image loader/writer, header-only C++11"
    license = "MIT"
    homepage = "https://github.com/syoyo/tinydng"
    url = "https://github.com/syoyo/tinydng"
    topics = ("dng", "tiff", "image", "header-only", "loader", "writer")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        # 上游没有自动化测试框架（CMakeLists 无 enable_testing/ctest）。
        # 真实执行上游唯一无外部依赖的测试入口 test_dng_loader（test_loader.cc，
        # 无断言、exit 恒 0 的冒烟程序），输入用上游源码树自带的 colorchart.dng，
        # 并校验解析输出中不出现 "Fail to load" 且包含图像元数据。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        log_path = os.path.join(self.build_folder, "upstream-test_dng_loader.log")
        if cross_building(self):
            # 交叉编译环境（x86 worker → aarch64）无法执行目标 ELF，只保留编译验证
            self.output.info("cross-building: skip upstream runtime smoke")
            return
        candidates = sorted(
            glob.glob(
                os.path.join(self.build_folder, "**", "test_dng_loader"), recursive=True
            )
        )
        if not candidates:
            raise ConanException("test_dng_loader binary not found in build folder")
        self.run(
            '"{}" "{}" > "{}" 2>&1'.format(
                candidates[-1],
                os.path.join(self.source_folder, "colorchart.dng"),
                log_path,
            ),
            cwd=self.build_folder,
        )
        log = load(self, log_path)
        if "Fail to load" in log:
            raise ConanException("upstream test_dng_loader failed to parse colorchart.dng")
        if "width =" not in log:
            raise ConanException("upstream test_dng_loader produced no image metadata")

    def package(self):
        src = self.source_folder
        inc = os.path.join(self.package_folder, "include")
        # 显式清单：glob 递归会把 examples/ 下的示例头（imgui 等）一并卷入
        for name in (
            "tiny_dng_loader.h",
            "tiny_dng_writer.h",
            "stb_image.h",
            "miniz.h",
            "miniz.c",
        ):
            copy(self, name, src, inc)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tinydng")
        self.cpp_info.set_property("cmake_target_name", "tinydng::tinydng")
        self.cpp_info.libs = []  # header-only，无编译产物
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
