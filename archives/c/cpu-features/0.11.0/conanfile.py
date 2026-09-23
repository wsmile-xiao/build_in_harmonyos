#!/usr/bin/env python3
"""Conan recipe for cpu_features 0.11.0 (google/cpu_features).

cpu_features 是 Google 的运行期 CPU 特性探测库（aarch64 下经 getauxval/hwcap
读取）。纯 C99 + CMake，零第三方运行时依赖（W0 预检通过）。

OHOS 适配要点：
- 上游 BUILD_TESTING=ON 时在 configure 期 execute_process 联网下载 googletest
  （cmake/googletest.CMakeLists.txt.in），沙箱无网络必失败 → patch 0001 换成
  find_package(GTest)（test_requires gtest/1.17.0，沿用 atracdenc 已验证的
  Conan gtest 集成模式），test/CMakeLists.txt 的 gtest/gmock_main 裸目标换成
  GTest:: 命名空间目标。
- aarch64 下上游启用 4 个测试二进制（bit_utils/string_view/stack_line_reader/
  cpuinfo_aarch64，共 30 个 TEST 用例），build() 内 ctest 全量实跑。
- 库本身静态编译（上游注释明确建议静态链接：位域布局实现定义，共享库跨
  编译器 ABI 不稳），shared 选项不暴露。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class CpuFeaturesConan(ConanFile):
    name = "cpu-features"
    version = "0.11.0"
    description = "A cross-platform C library to retrieve CPU features (Google)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/cpu_features"
    url = ""  # CI fills this
    topics = ("cpu", "features", "detection", "hwcaps")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # 上游 BUILD_TESTING 需要 googletest。必须用 1.17.0.1：其 package_info
        # 声明 GTest::gmock_main 等组件目标；1.17.0 是扁平 gtest::gtest 布局，
        # find_package(GTest) 后无 GTest::gmock_main → configure 报 target
        # not found（CI #43932 实测，celero/2.10.0 同款用法已验证发布）。
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = "ON"
        tc.cache_variables["BUILD_EXECUTABLE"] = "ON"
        # 注：CMAKE_SYSTEM_PROCESSOR 的 HarmonyOS unknown 回落由
        # patches/0002-ohos-arch-fallback.patch 处理——cache_variables 会被
        # conan_toolchain.cmake 自身的 set() 遮蔽（CI #43837 实测无效）。
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 层1：上游 gtest 套件（aarch64 4 个二进制/30 用例）全量实跑
        self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cpu_features"]
        self.cpp_info.includedirs = [os.path.join("include", "cpu_features"), "include"]
