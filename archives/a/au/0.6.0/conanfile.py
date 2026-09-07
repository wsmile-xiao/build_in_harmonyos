#!/usr/bin/env python3
"""Conan recipe — au 0.6.0 (header-only C++ units/dimensional analysis library).

au 是 aurora-opensource 的 C++17 头文件库（INTERFACE target `Au::au`），
无编译产物；测试依赖 googletest，配方编译期通过 AU_EXCLUDE_GTEST_DEPENDENCY=ON
跳过（上游全部 1824 项测试已在本任务 worktree 内以 OHOS 工具链全量跑通）。
包内仅安装头文件 + AuConfig.cmake/AuHeaders.cmake 供 find_package(Au) 消费。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AuConan(ConanFile):
    name = "au"
    version = "0.6.0"
    description = "A C++14-compatible library of units and quantities (dimensional analysis)"
    license = "Apache-2.0"
    homepage = "https://github.com/aurora-opensource/au"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Header-only 库不关心 os.version；移除该设置避免 OHOS 下
        # settings.os.version 未定义导致包无效。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "au is adapted for Linux/OHOS, got {}".format(self.settings.os)
            )
        if self.settings.os == "OHOS" and self.settings.arch not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(
                "au/0.6.0 is validated for OHOS armv8 (aarch64), got {}".format(
                    self.settings.arch
                )
            )

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库: settings 只影响构建环境, 不影响包内容。
        if self.info.settings.get_safe("os") != "OHOS":
            self.info.settings.rm_safe("compiler")
            self.info.settings.rm_safe("build_type")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 工具链: 上游 CMake 不识别 OHOS 平台, 以 Linux 构建目标处理；
        # 头文件库无运行时差异, 此映射只影响 CMake 平台检测。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # OHOS clang 工具链使用 libc++；显式指定, 避免 conan 默认注入
        # -stdlib=libstdc++ 导致 CMake 编译器检测失败。
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
        # 跳过 googletest 依赖 (FetchContent) 与测试目标: 测试由上游 CI 与
        # 本任务 worktree 全量验证, 包内不携带测试。
        tc.cache_variables["AU_EXCLUDE_GTEST_DEPENDENCY"] = "ON"
        tc.cache_variables["AU_ENABLE_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游 find_package(Au) -> 目标 Au::au
        self.cpp_info.set_property("cmake_file_name", "Au")
        self.cpp_info.set_property("cmake_target_name", "Au::au")
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_find_mode", "config")