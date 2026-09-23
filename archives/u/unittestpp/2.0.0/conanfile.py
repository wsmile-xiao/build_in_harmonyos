#!/usr/bin/env python3
"""Conan recipe — unittestpp 2.0.0（UnitTest++ 轻量 C++ 单元测试框架）。

上游：https://github.com/unittest-cpp/unittest-cpp （v2.0.0, 2017-01-13, MIT）

OHOS 适配要点（零源码补丁）：
- 上游 CMakeLists.txt 声明 cmake_minimum_required(VERSION 2.8.1)，CMake 4.x
  已移除 <3.5 兼容 —— 通过 cmake 命令行传 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  放行（CMake 官方旧项目兼容开关，无需补丁）。
- 平台层 UnitTest++/Posix/（gettimeofday/usleep + sigsetjmp/sigaction 信号
  翻译）在 OHOS musl 上原生可用；Config.h 依据编译器三元组
  （aarch64-unknown-linux-ohos，定义 __unix__/linux 系宏）自动选中 Posix 路径。
- 上游构建系统默认 STATIC（add_library(UnitTest++ STATIC ...)），本配方保持
  静态库；shared 选项显式拒绝（validate）。
- 上游测试套件 tests/（TestUnitTest++，21 个测试源文件 + Main.cpp）随构建自动编译，
  上游 CMakeLists 以 POST_BUILD 方式在构建期执行；本配方 build() 末尾再显式运行
  一次并解析结果（HMBS_UPSTREAM_TEST_RESULT 行），用例数不符或存在失败即中止
  构建（CI 与本机同一咽喉）。计数口径：上游源码清点 277（含 9 个
  UNITTEST_USE_CUSTOM_STREAMS 专属用例），Release/默认构建实测 268/267（见 manifest）。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)


class UnitTestppConan(ConanFile):
    name = "unittestpp"
    version = "2.0.0"
    description = "UnitTest++ — a lightweight unit testing framework for C++"
    license = "MIT"
    homepage = "https://github.com/unittest-cpp/unittest-cpp"
    url = "https://github.com/unittest-cpp/unittest-cpp"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # 本构建配置（Release/NDEBUG、默认 std::ostringstream）下上游测试实际执行的用例数
    # （OHOS 真机实测：268 全过）。作为覆盖率护栏：执行数变化时显式失败。
    # 说明：上游源码清点 277 用例（含 9 个 UNITTEST_USE_CUSTOM_STREAMS 专属用例，
    # 与平台审查口径一致）；默认构建配置实测 267（差 1 个 NDEBUG-only 崩溃用例）。
    UPSTREAM_TEST_CASES = 268

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # 上游 CMakeLists 硬编码 add_library(... STATIC ...)，共享库需改上游
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "unittestpp upstream CMakeLists only builds a static library")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 静态库位置无关代码（供下游链接进共享库；与 unqlite 等同惯例）
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            "ON" if self.options.get_safe("fPIC", True) else "OFF")
        # 显式声明：构建上游测试套件 TestUnitTest++（上游 CMakeLists
        # 以 POST_BUILD 方式在构建期自动执行它）
        tc.variables["UTPP_INCLUDE_TESTS_IN_BUILD"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        self._run_upstream_tests()

    def _find_test_binary(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "TestUnitTest++" in files:
                return os.path.join(root, "TestUnitTest++")
        raise ConanException(
            "上游测试可执行文件 TestUnitTest++ 未找到（构建可能未包含 tests/）")

    def _run_upstream_tests(self):
        """显式运行一次上游测试并输出结构化结果（HMBS_UPSTREAM_TEST_RESULT）。

        被测对象是本次刚构建出的静态库；任一用例失败或数量不符即抛错，
        使 conan create 失败（CI 与本地 W3 同一咽喉）。
        """
        binary = self._find_test_binary()
        log = os.path.join(self.build_folder, "upstream-test-run.log")
        rc = self.run('"%s" > "%s" 2>&1' % (binary, log), ignore_errors=True)
        output = load(self, log)

        passed = None
        failed_tests = None
        for line in output.splitlines():
            if line.startswith("Success: "):
                passed = int(line.split()[1])
            elif line.startswith("FAILURE: "):
                failed_tests = int(line.split()[1])

        summary = {
            "source": "upstream tests/ (TestUnitTest++, unmodified)",
            "expected_total": self.UPSTREAM_TEST_CASES,
            "passed": passed,
            "failed_tests_reported": failed_tests,
            "exit_code": rc,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary, ensure_ascii=False))

        if rc != 0 or passed != self.UPSTREAM_TEST_CASES:
            raise ConanException(
                "上游测试未全部通过（rc=%s, passed=%s, 期望 %d）：\n%s"
                % (rc, passed, self.UPSTREAM_TEST_CASES, output[-2000:]))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["UnitTest++"]
        # 与上游安装树导出的名称保持一致（cmake/UnitTest++Config.cmake，
        # 目标名无命名空间）：消费者 find_package(UnitTest++) + 链接 UnitTest++
        self.cpp_info.set_property("cmake_file_name", "UnitTest++")
        self.cpp_info.set_property("cmake_target_name", "UnitTest++")
