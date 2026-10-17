#!/usr/bin/env python3
"""Conan recipe — uchardet 0.0.7 on HarmonyOS PC (aarch64).

uchardet is an encoding detector library forked from Mozilla's Universal
Charset Detector.  Upstream build is CMake (declares cmake_minimum_required
2.8.5) with no external dependencies: one C++ library (libuchardet), one
C API header (uchardet/uchardet.h) and a CLI tool (uchardet).

Historical note (2026-05-25 archive, status=built): the same source builds
cleanly natively on OHOS with clang; the only quirk is the ancient
cmake_minimum_required, handled via CMAKE_POLICY_VERSION_MINIMUM.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class UchardetConan(ConanFile):
    name = "uchardet"
    version = "0.0.7"
    description = "Encoding detector library forked from Mozilla's Universal Charset Detector"
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/uchardet/"
    url = "https://gitlab.freedesktop.org/uchardet/uchardet"
    topics = ("charset", "encoding", "detector", "mozilla")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C++ 库，无第三方依赖
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游声明 cmake_minimum_required(2.8.5)，CMake >= 4.0 拒绝低于
        # 3.5 的兼容级别。必须以 cache 变量传入（命令行 -D），普通
        # tc.variables 只写入 toolchain 的 set()，对 cmake_minimum_required
        # 太晚不生效（历史归档验证过的参数）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 本机构建时 CMake 自检为未知平台 "HarmonyOS"：无共享库
        # SONAME/版本化规则，libuchardet.so 无 SONAME、CLI 工具记录
        # 相对路径 NEEDED（../libuchardet.so）无法在包外解析。本包为
        # 纯算法库无平台分支，显式按 Linux 平台规则构建（SONAME=
        # libuchardet.so.0，NEEDED 可经 LD_LIBRARY_PATH 解析）。
        # 参考 archives/a/abcmidi 同款处理。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        # 上游 option(BUILD_BINARY) 默认 ON：CLI 工具随库一起构建安装。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # L1: 上游测试套件（ctest 语料库检测，116 项，全部断言）
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["uchardet"]
        # 上游 BUILD_BINARY=ON：包同时提供 bin/uchardet CLI 工具（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "uchardet")
        self.cpp_info.set_property("cmake_target_name", "uchardet::uchardet")
        self.cpp_info.set_property("pkg_config_name", "uchardet")
