#!/usr/bin/env python3
"""Conan recipe — logfault 0.5.2 (header-only C++ logging library).

logfault 是单头文件（include/logfault/logfault.h）header-only C++ 日志库，零运行依赖、
无编译产物：
- package_type = "header-library" + implements auto_header_only_mode；
- package() 只交付 include/logfault/*.h 与 licenses/LICENSE；
- 上游测试面（rule4/R51）：上游 CMake（根 CMakeLists.txt `LOGFAULT_BUILD_TESTS=ON`）
  驱动 tests/ 下 2 个 gtest 可执行（default_to_clog 与 default_to_clog_with_tid
  同源各编一次，后者带 LOGFAULT_USE_TID_AS_NAME=1），经 ctest 执行。
  本配方 build() = configure + build + ctest -V，把上游用例真跑进 G2/W3 证据链。
- 计数口径（候选数法取最大）：源码宏 7（5 无条件 + 2 平台门控 HelloTid），
  框架注册 11（5 + 6，linux 门控 HelloTid 在 __linux__ 上随 TID 变体注册），
  断言点 7（EXPECT_TRUE 源码位）/ 运行期断言 11 —— N=11。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.scm import Version


class LogfaultConan(ConanFile):
    name = "logfault"
    version = "0.5.2"
    description = "Simple to use, header only C++ library for application-logging on all major platforms."
    license = "MIT"
    homepage = "https://github.com/jgaa/logfault"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("logging", "header-only")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "arch", "compiler", "build_type"
    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    # 上游测试（build() 内 cmake/ctest）与消费者测试（test_package）都走 CMake
    generators = "CMakeDeps", "CMakeToolchain"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 tests/CMakeLists.txt 硬依赖 GTest（find_package(GTest REQUIRED)）；
        # ohpcd registry 有 gtest/1.17.0 二进制（armv8/OHOS/clang15/libc++/Release）
        if not self.conf.get("tools.build:skip_test", default=False):
            self.test_requires("gtest/1.17.0")

    @property
    def _min_cppstd(self):
        # 与 CCI recipes/logfault/all/conandata.yml 同口径（上游 conanfile 自报 14，
        # CCI 收紧到 17；profile compiler.cppstd=17 恒满足）
        return 17

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = {
            "Visual Studio": "15",
            "msvc": "191",
            "gcc": "8",
            "clang": "7",
            "apple-clang": "12",
        }.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"logfault requires C++{self._min_cppstd}, but the compiler is too old.")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── 上游测试集成（R51 上游测试三步法）────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        if self.conf.get("tools.build:skip_test", default=False):
            return
        cmake = CMake(self)
        # 上游根 CMakeLists 默认即 ON，这里显式钉死防 conf 影响
        cmake.configure(variables={"LOGFAULT_BUILD_TESTS": "ON"})
        # 并行度上限：Conan 的 CMake helper 无条件追加 `-j<tools.build:jobs>`，
        # 该 conf 缺省取 os.cpu_count()（本机与 CI worker 均 20、affinity 8 → 2.5×
        # 超订），CI 内存受限窗口里 -j20 触发 fork 耗尽被报成「编译失败」。
        # 先例：archives/e/erkir/2.1.1（CI #62527 实测）、openjpeg2/librtpi 同族。
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 2)
        cmake.build()
        # ctest -V 把每个 gtest 可执行的汇总行打进 G2/W3 日志：
        #   [==========] N tests from M suites ran.
        #   [  PASSED  ] N tests.
        # 两个二进制：default_to_clog(5) + default_to_clog_with_tid(6) = 11
        self.run("ctest --output-on-failure -V", cwd=self.build_folder)

    # ── 打包 ────────────────────────────────────────────────────────────
    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "logfault")
        self.cpp_info.set_property("cmake_target_name", "logfault::logfault")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
