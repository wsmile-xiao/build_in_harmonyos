#!/usr/bin/env python3
"""Conan recipe — snitch 1.2.3 (CMake, C++20 轻量测试框架库).

snitch（snitch-org/snitch）是零运行依赖的 C++20 单元测试框架，产物为
libsnitch（静态/动态，或 header-only 变体），无命令行工具（纯库包，
无 commands.json —— PF8 同口径）。

配方对齐 CCI `recipes/snitch/all`（W0 同源：conandata URL/sha256 与 CCI
逐字一致，2026-09-25 设备实测复算），并做 OHOS 侧两处适配：

  * CI profile 默认 `compiler.cppstd=17`，而 snitch 的 CMake target 全部
    `target_compile_features(cxx_std_20)`（上游 CMakeLists.txt:137/172/
    225/240），CCI 的 `check_min_cppstd(20)` validate 会直接判
    ConanInvalidConfiguration —— 按 abseil/arrow 先例在 configure() 中
    把 cppstd 覆盖为 20（package_id 随之含 cppstd=20，语义正确）。
  * 上游 tests/（runtime + approval 两套）由 doctest 驱动（FetchContent
    拉 github.com/doctest/doctest v2.4.9），且 approval 用例的路径归一化
    正则硬编码 `/snitch/tests/`（上游 CI checkout 目录名）—— 配方构建
    保持 CCI 同款 `SNITCH_DO_TEST=FALSE`（不联网不拉 doctest），上游测试
    在设备原生构建侧按上游预期布局独立运行（见 notes.md 与
    reports/test-report.md），test_package 从消费者视角验证已打包制品。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.scm import Version
import os


class SnitchConan(ConanFile):
    name = "snitch"
    version = "1.2.3"
    description = "Lightweight C++20 testing framework"
    license = "BSL-1.0"
    homepage = "https://github.com/snitch-org/snitch"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("snitch", "unit-test", "testing-framework")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "header_only": [True, False],
        "with_main": [True, False],
        "with_exceptions": [True, False],
        "with_timings": [True, False],
        "with_shorthand_macros": [True, False],
        "with_default_color": [True, False],
        "with_success_decompose": [True, False],
        "with_reporters": [None, "ANY"],
        "max_test_cases": ["ANY"],
        "max_nested_sections": ["ANY"],
        "max_expr_length": ["ANY"],
        "max_message_length": ["ANY"],
        "max_test_name_length": ["ANY"],
        "max_tag_length": ["ANY"],
        "max_captures": ["ANY"],
        "max_capture_length": ["ANY"],
        "max_unique_tags": ["ANY"],
        "max_command_line_args": ["ANY"],
        "max_registered_reporters": ["ANY"],
        "max_path_length": ["ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "header_only": False,
        "with_main": True,
        "with_exceptions": True,
        "with_timings": True,
        "with_shorthand_macros": True,
        "with_default_color": True,
        "with_success_decompose": False,
        "with_reporters": "all",
        "max_test_cases": 5000,
        "max_nested_sections": 8,
        "max_expr_length": 1024,
        "max_message_length": 1024,
        "max_test_name_length": 1024,
        "max_tag_length": 256,
        "max_captures": 8,
        "max_capture_length": 256,
        "max_unique_tags": 1024,
        "max_command_line_args": 1024,
        "max_registered_reporters": 8,
        "max_path_length": 1024,
    }

    _min_cppstd = "20"

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "10",
            "Visual Studio": "17",
            "msvc": "193",
            "clang": "10",
            "apple-clang": "10",
        }

    @property
    def _available_reporters(self):
        return ["xml", "teamcity"]

    def requirements(self):
        # 零运行依赖（W0-2 实查：CCI recipe 无 requirements/build_requirements；
        # 仅 Linux/OHOS 侧 system lib m，见 package_info）
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # CI profile 默认 cppstd=17（ci/conan/profiles/ohos-aarch64），snitch
        # 强制 C++20 —— 覆盖为 20，否则 validate 的 check_min_cppstd(20)
        # 直接 ConanInvalidConfiguration（arrow 25.0.0 / abseil 同款先例）。
        self.settings.compiler.cppstd = "20"

        if self.options.shared or self.options.header_only:
            self.options.rm_safe("fPIC")

        if self.options.header_only:
            del self.options.shared

    def package_id(self):
        if self.info.options.header_only:
            # header-only：编译器/平台无关，但选项影响生成的头内容，不清选项
            self.info.settings.clear()

    def export_sources(self):
        # conandata.yml 声明空补丁集（patches: {}）；导出钩子保持 G1 完整
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(
            str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, "
                f"but {self.settings.compiler} {self.settings.compiler.version} "
                f"is too old")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 库包默认静态（shared 选项驱动 BUILD_SHARED_LIBS）
        tc.cache_variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")

        # 与 CCI 同款：不构建上游测试（doctest 需 FetchContent 联网，
        # 且 approval 用例对源码路径布局敏感——见模块 docstring）
        tc.cache_variables["SNITCH_DO_TEST"] = False
        tc.cache_variables["SNITCH_UNITY_BUILD"] = True

        # 库形态
        tc.cache_variables["SNITCH_HEADER_ONLY"] = bool(self.options.header_only)

        # 特性开关（与 CCI 同款）
        tc.cache_variables["SNITCH_DEFINE_MAIN"] = bool(self.options.with_main)
        tc.cache_variables["SNITCH_WITH_EXCEPTIONS"] = bool(self.options.with_exceptions)
        tc.cache_variables["SNITCH_WITH_TIMINGS"] = bool(self.options.with_timings)
        tc.cache_variables["SNITCH_WITH_SHORTHAND_MACROS"] = bool(
            self.options.with_shorthand_macros)
        tc.cache_variables["SNITCH_DEFAULT_WITH_COLOR"] = bool(
            self.options.with_default_color)
        tc.cache_variables["SNITCH_DECOMPOSE_SUCCESSFUL_ASSERTIONS"] = bool(
            self.options.with_success_decompose)

        for reporter in str(self.options.with_reporters).split(","):
            reporter = reporter.strip()
            if reporter == "all":
                tc.cache_variables["SNITCH_WITH_ALL_REPORTERS"] = True
                break
            if reporter in self._available_reporters:
                tc.cache_variables["SNITCH_WITH_ALL_REPORTERS"] = False
                tc.cache_variables[f"SNITCH_WITH_{reporter.upper()}_REPORTER"] = True
            else:
                raise ConanInvalidConfiguration(
                    f"unknown reporter '{reporter}'")

        # 可配置上限（与 CCI 同款）
        tc.cache_variables["SNITCH_MAX_TEST_CASES"] = str(self.options.max_test_cases)
        tc.cache_variables["SNITCH_MAX_NESTED_SECTIONS"] = str(
            self.options.max_nested_sections)
        tc.cache_variables["SNITCH_MAX_EXPR_LENGTH"] = str(self.options.max_expr_length)
        tc.cache_variables["SNITCH_MAX_MESSAGE_LENGTH"] = str(
            self.options.max_message_length)
        tc.cache_variables["SNITCH_MAX_TEST_NAME_LENGTH"] = str(
            self.options.max_test_name_length)
        tc.cache_variables["SNITCH_MAX_TAG_LENGTH"] = str(self.options.max_tag_length)
        tc.cache_variables["SNITCH_MAX_CAPTURES"] = str(self.options.max_captures)
        tc.cache_variables["SNITCH_MAX_CAPTURE_LENGTH"] = str(
            self.options.max_capture_length)
        tc.cache_variables["SNITCH_MAX_UNIQUE_TAGS"] = str(self.options.max_unique_tags)
        tc.cache_variables["SNITCH_MAX_COMMAND_LINE_ARGS"] = str(
            self.options.max_command_line_args)
        tc.cache_variables["SNITCH_MAX_REGISTERED_REPORTERS"] = str(
            self.options.max_registered_reporters)
        tc.cache_variables["SNITCH_MAX_PATH_LENGTH"] = str(self.options.max_path_length)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # 消费者走 conan 生成的 CMakeDeps 配置，不装上游 find_package 包装
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        target = "snitch-header-only" if self.options.header_only else "snitch"

        self.cpp_info.set_property("cmake_file_name", "snitch")
        self.cpp_info.set_property("cmake_target_name", f"snitch::{target}")
        self.cpp_info.set_property("pkg_config_name", "snitch")

        if self.options.header_only:
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
        else:
            self.cpp_info.libs = ["snitch"]
            # CCI 对 Linux/FreeBSD 记 m；OHOS 同为 POSIX 用户态，沿用
            if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
                self.cpp_info.system_libs.append("m")
