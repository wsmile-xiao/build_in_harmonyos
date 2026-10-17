#!/usr/bin/env python3
"""Conan recipe — veccore 0.8.1（VecCore，C++ 可移植 SIMD 向量化抽象层）。

上游 CMake 目标是 `add_library(VecCore INTERFACE)`，即纯头文件库；后端可选
Vc / UME::SIMD / std::experimental::simd / 标量。OHOS aarch64（clang 15 +
libc++，C++17）上真正生效的后端是 Scalar 与 ScalarWrapper：Vc/UMESIMD/CUDA
显式关闭，std::experimental::simd 需要 C++20 且 libc++ 未提供该头。

上游测试（test/*.cc，GoogleTest）在 BUILD_TESTING=ON 时构建；本配方另开
DETAILED_TEST_REPORT=ON 让 gtest_discover_tests 把每个 gtest 用例注册成独立
ctest 用例，并在 build() 内真实执行 ctest（默认关时 8 个测试文件只会折成
1 条 ctest 用例）。GoogleTest 用上游仓库自带的 builtins/googletest 快照
（BUILD_GOOGLETEST=ON），因此本包零外部 conan 依赖。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# 上游 test/*.cc 中 GoogleTest 宏声明总数（取数命令见 notes.md）
UPSTREAM_DECLARED_CASES = 47
# ctest --output-junit 产物，用于把「实跑用例数」写成可核对的证据
CTEST_JUNIT = "upstream-ctest.xml"


class VeccoreConan(ConanFile):
    name = "veccore"
    version = "0.8.1"
    description = (
        "C++ library for portable SIMD vectorization: an architecture-"
        "independent API over Vc, UME::SIMD, std::experimental::simd and "
        "scalar backends"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/root-project/veccore"
    url = "https://github.com/root-project/veccore"
    topics = ("simd", "vectorization", "header-only", "veccore")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # conan 不写 CMAKE_SYSTEM_NAME 时 CMake 退回 `uname -s` 的 "HarmonyOS"，
        # 而它只带 Modules/Platform/OHOS.cmake，平台变量会全部留空
        # （与已合入的 vdt 0.4.4 同一处理）。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，统一成 lib/ 与 cpp_info 一致。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 上游 project(VecCore) 把 CMAKE_CXX_STANDARD 写成 11（CACHE），而仓库
        # 自带的 googletest 快照用了 GTEST_ALLOW_UNINSTANTIATED_PARAMETERIZED_TEST
        # （1.11+ 才有的宏，需要 C++14）；profile 的 cppstd=17 不会自动落进这个
        # cache 变量，必须显式传。
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # builtins/googletest 声明 cmake_minimum_required(VERSION 2.8.12)，
        # CMake 4.x 已移除 <3.5 兼容（真机 cmake 4.4.3）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 可选后端在 aarch64/OHOS 上不可用；基准与文档不参与验证。
        tc.variables["VC"] = False
        tc.variables["UMESIMD"] = False
        tc.variables["CUDA"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_GOOGLEBENCH"] = False
        tc.variables["BUILD_DOCS"] = False
        # 上游测试套件 + 仓库自带 googletest 快照。
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_GOOGLETEST"] = True
        # EXCLUDE_FROM_ALL 不影响 install 规则，必须显式关掉 gtest 自身的安装，
        # 否则静态库与 gtest 头会被装进这个 header-only 包。
        tc.variables["INSTALL_GTEST"] = False
        # 每个 gtest 用例注册成独立 ctest 用例。
        tc.variables["DETAILED_TEST_REPORT"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """真实执行上游 GoogleTest 套件（test-backends），逐 ctest 用例取证。"""
        if not can_run(self):
            self.output.info(
                "cross-building：上游 test-backends 已编译，执行由真机 conan create 覆盖"
            )
            return
        junit = os.path.join(self.build_folder, CTEST_JUNIT)
        self.run('ctest --test-dir "%s" --output-on-failure --output-junit %s'
                 % (self.build_folder, CTEST_JUNIT), cwd=self.build_folder,
                 env="conanbuild")
        total, failed = self._parse_ctest_junit(junit)
        if failed:
            raise Exception("上游 ctest 有 %d/%d 个用例失败" % (failed, total))
        self.output.info("上游测试实跑完成：%d/%d 通过（ctest --output-junit %s）"
                         % (total, total, CTEST_JUNIT))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "framework": "gtest+ctest",
            "source_declared_total": UPSTREAM_DECLARED_CASES,
            "executed": total,
            "passed": total,
            "failed": 0,
            "skipped": 0,
            "note": (
                "upstream test/*.cc declare %d gtest cases; the suites are "
                "typed-parameterized and instantiate per backend and per "
                "vector type, so ctest reports %d cases with only the Scalar "
                "and ScalarWrapper backends enabled" % (UPSTREAM_DECLARED_CASES, total)
            ),
        }, ensure_ascii=False))

    def _parse_ctest_junit(self, path):
        if not os.path.isfile(path):
            raise Exception("缺少 ctest JUnit 报告，无法取证上游用例数：%s" % path)
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read(65536)
        tests = re.search(r'tests="(\d+)"', text)
        if not tests:
            raise Exception("ctest JUnit 报告里没有 tests= 属性：%s" % path)
        failed = 0
        for attr in ("failures", "errors"):
            match = re.search(r'%s="(\d+)"' % attr, text)
            if match:
                failed += int(match.group(1))
        return int(tests.group(1)), failed

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 上游把 FindUMESIMD.cmake 与生成的 VecCoreConfig.cmake 装进 lib/cmake/，
        # 与 conan CMakeDeps 给消费方生成的 config 重名；header-only 包对外只需
        # 要 include/，故整棵 lib/ 移除。
        shutil.rmtree(os.path.join(self.package_folder, "lib"), ignore_errors=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "VecCore")
        self.cpp_info.set_property("cmake_target_name", "VecCore::VecCore")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
