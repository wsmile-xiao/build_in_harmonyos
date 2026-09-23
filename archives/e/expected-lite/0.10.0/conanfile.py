#!/usr/bin/env python3
"""Conan recipe — expected-lite 0.10.0 (CMake header-only library).

expected-lite 是 std::expected 的 C++11/14/17/20 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class ExpectedLiteConan(ConanFile):
    name = "expected-lite"
    version = "0.10.0"
    description = "Expected objects for C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/expected-lite"
    url = ""  # CI fills this
    topics = ("expected", "header-only", "cpp11", "cpp17", "cpp20")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform.
        # OHOS 的 Conan arch=armv8 不能直接作为 CMAKE_SYSTEM_PROCESSOR，需映射为 aarch64；
        # Linux 保留实际架构值（str(self.settings.arch)），避免 x86_64 等场景被错误覆盖。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # 集成上游测试用例 (lest 框架, CTest: cpp11/cpp14/cpp17/cpp20)
        tc.variables["EXPECTED_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["EXPECTED_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()
        # E266: OHOS SDK 的 lld 动态依赖 libxml2.so.16，部分 CI worker 默认库
        # 搜索路径找不到它导致链接失败；前置 SDK llvm/lib（内含 libxml2.so.16）
        # 到 LD_LIBRARY_PATH 让 lld 正常启动（abuild/aeolus 同方案）。
        # 注意：不能改用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS 沙箱中
        # Permission denied (exit 126) 不可执行（需 ELF 签名），lld 产物可执行。
        if self.settings.os == "OHOS":
            env = Environment()
            env.prepend_path(
                "LD_LIBRARY_PATH",
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
            )
            env.vars(self).save_script("conanbuildenv_ohos_llvm")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "expected-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::expected-lite")
        self.cpp_info.libs = []
