#!/usr/bin/env python3
"""Conan recipe — cdt 1.4.5 (C++ constrained Delaunay triangulation, header-only / optional compiled).

上游配方保留（MPL-2.0）：https://github.com/artem-ogre/CDT
OHOS 适配要点：
- R32: settings.os 判断使用 in ("Linux", "OHOS")
- E092/E267: CMake 不识别 OHOS 平台名 -> 显式覆写 CMAKE_SYSTEM_NAME=Linux（HarmonyOS 基于 Linux 内核）
- catch2 改为仅 enable_testing=True 时要求（上游无条件 require catch2/3.4.0；制品仓已发布 2.13.10-r0，
  测试源码宏面与其兼容，配合 include 适配补丁 0001/0002）
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
import os, shutil


class CDTConan(ConanFile):
    name = "cdt"
    version = "1.4.5"
    license = "MPL-2.0"
    homepage = "https://github.com/artem-ogre/CDT"
    url = ""  # CI fills this
    description = "Numerically robust C++ implementation of constrained Delaunay triangulation (CDT)"
    topics = ("triangulation", "delaunay", "geometry", "header-only", "cpp11")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"

    options = {
        "shared": [True, False],
        "as_compiled_library": [True, False],
        "enable_testing": [True, False],
        "enable_callback_handler": [True, False],
        "enable_64_bit_index_type": [True, False],
    }
    default_options = {
        "shared": False,
        "as_compiled_library": False,
        "enable_testing": False,
        "enable_callback_handler": False,
        "enable_64_bit_index_type": False,
    }

    exports_sources = "patches/*"
    generators = "CMakeDeps"  # catch2(测试依赖) 经 CMakeDeps 提供 Catch2Config/Catch2::Catch2

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 仅测试路径需要 Catch2（制品仓已发布 2.13.10-r0；上游标注的 3.4.0 未发布，
        # 测试宏面与 2.13 兼容——见 notes.md 与补丁说明）
        if self.options.enable_testing:
            self.requires("catch2/2.13.10-r0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游为 monorepo：实际 CMake 工程位于源码树嵌套的 CDT/ 子目录。
        # 将 CDT/ 内容上移到 source 根，使补丁路径（a/CMakeLists.txt）与
        # 本地 .work 双轨结构一致（refresh-patch 同口径）。
        proj = os.path.join(self.source_folder, "CDT")
        if os.path.isdir(proj):
            for entry in os.listdir(proj):
                shutil.move(os.path.join(proj, entry), os.path.join(self.source_folder, entry))
            os.rmdir(proj)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CDT_USE_AS_COMPILED_LIBRARY"] = self.options.as_compiled_library
        tc.cache_variables["CDT_ENABLE_TESTING"] = self.options.enable_testing
        tc.cache_variables["CDT_ENABLE_CALLBACK_HANDLER"] = self.options.enable_callback_handler
        tc.cache_variables["CDT_USE_64_BIT_INDEX_TYPE"] = self.options.enable_64_bit_index_type
        # E092/E267: OHOS 视为 Linux 平台（CDT 无平台相关代码，公开 API 纯头文件逻辑）
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.enable_testing and not cross_building(self):
            self.output.info("Running upstream CDT tests via CTest")
            env = Environment()
            env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            with env.vars(self).apply():
                cmake.test(cli_args=["--verbose"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 默认 INTERFACE(header-only)：collect_libs 为空 -> 无 libs；
        # CDT_USE_AS_COMPILED_LIBRARY=ON 时产 libCDT(a)
        # 与上游 install(EXPORT CDTConfig NAMESPACE CDT::) 对齐：消费者 find_package(CDT) 得 CDT::CDT
        self.cpp_info.set_property("cmake_file_name", "CDT")
        self.cpp_info.set_property("cmake_target_name", "CDT::CDT")
        self.cpp_info.libs = collect_libs(self)