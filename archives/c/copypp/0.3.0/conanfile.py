#!/usr/bin/env python3
"""Conan recipe — copypp 0.3.0 (header-only C++ field-copy utility).

copypp 是 header-only C++ 库（include/icurve/{copypp,copypp_only,meta}.hh），
交付物只有头文件，零运行期依赖（纯 C++20 标准库）。

适配决策与依据（2026-09-26 设备实测）：
1. 上游测试树的开关：根 CMakeLists 用 ``if(COPYPP_TEST)`` 决定是否
   ``enable_testing() + add_subdirectory(test)``；上游 GitHub Actions
   （.github/workflows/cmake-multi-platform.yml）显式传 ``-DCOPYPP_TEST=OFF``
   ——即**上游 CI 根本不构建、不运行 test/ 下的 7 个 GoogleTest 目标**。
   本适配按 R51 三步法自行清点（源码宏 33）并在 ``build()`` 内真实构建运行。
2. 上游 test/CMakeLists.txt 只给**部分**目标链接 fmt：A.h 一律
   ``#include <fmt/core.h>``，而 copypp_test3/copypp_test4/copypp_array_test
   没有链接 fmt；nlohmann/json.hpp 则被 3 个测试 include 却**没有任何目标链接它**
   ——上游是在 ``/usr/include`` 系统头齐备的机器上这样写的。设备上这些头由
   Conan 依赖提供，故按 CMake「Code Injection」机制（``CMAKE_PROJECT_INCLUDE``，
   cmake ≥3.15 官方注入点，专用于"不修改上游源码地注入构建逻辑"）把
   fmt / nlohmann_json 的头目录注入根工程作用域，等价于系统 include 路径。
   **零上游文件改动、零补丁。**
3. ``GTest_DIR`` / ``fmt_DIR`` 指向 Conan 包**自带的上游 CMake config**：
   gtest 包 ``lib/cmake/GTest/GTestConfig.cmake``（定义 ``GTest::gtest`` /
   ``GTest::gtest_main``）、fmt 包 ``lib/cmake/fmt/fmt-config.cmake``（定义
   ``fmt::fmt`` 与 ``fmt::fmt-header-only``）。Conan CMakeDeps 自己生成的
   config 只有 ``gtest::gtest`` / ``fmt::fmt`` 两目标，与上游
   ``find_package(GTest CONFIG REQUIRED)`` + ``GTest::gtest_main`` +
   ``fmt::fmt-header-only`` 的写法对不上（实测 configure/generate 阶段报
   target not found）。
4. ``-UNDEBUG``：上游 copypp_test / copypp_test2 的检查用 C ``assert()``
   （0 个 gtest EXPECT/ASSERT 宏），Release 默认 ``-DNDEBUG`` 会把它们编译成
   空转；注入 ``-UNDEBUG`` 让断言真实生效——该方向只会暴露更多失败，
   不会减少失败，且不动上游一行代码。
5. C++20：上游 ``set(CMAKE_CXX_STANDARD 20)`` 且头文件里有
   ``#error "minimun c++ version is c++20."``；conan profile 的
   ``compiler.cppstd=17`` 由上游 CMakeLists 的 normal set() 覆盖（CMake 实测
   警告后按 20 编译，命令行 ``-std=c++20``），故**不调用 check_min_cppstd(20)**
   （settings 面是 17，调用必失败且与真实编译面不符）。
"""
import json
import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游 test/ 下 7 个 GoogleTest 目标（test/CMakeLists.txt 的 add_executable 清单）
_UPSTREAM_TEST_BINARIES = (
    "copypp_test",
    "copypp_test2",
    "copypp_only_test",
    "copypp_test3",
    "copypp_test4",
    "copypp_array_test",
    "copypp_stl_test",
)


class CopyppConan(ConanFile):
    name = "copypp"
    version = "0.3.0"
    description = "copypp — header-only C++ utility for copying fields across structs/arrays/containers and between struct and JSON string"
    license = "MIT"
    homepage = "https://github.com/i-curve/copypp"
    url = "https://github.com/i-curve/copypp"
    topics = ("copy", "struct", "header-only", "json")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"
    # 源码只读：build()/package() 直接从 source_folder 读取
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    # 上游测试树的构建期依赖（仅本包 build() 用；test_requires 不传播给消费者，
    # 交付依赖仍为 0 —— manifest build.dependencies == []）
    def build_requirements(self):
        self.test_requires("gtest/1.17.0")
        self.test_requires("fmt/11.1.3")
        self.test_requires("nlohmann_json/3.12.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # 上游钉 CMAKE_CXX_STANDARD 20（头文件 #error 亦要求 C++20）；
        # conan toolchain 默认写 17，这里把缓存值对齐到 20，消除
        # "Standard CMAKE_CXX_STANDARD value ... has been modified" 警告。
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "20"
        # 显式打开上游测试树（上游 CI 传 OFF，本适配必须开）
        tc.cache_variables["COPYPP_TEST"] = "ON"

        # 用 Conan 包自带的上游 CMake config，保住 GTest::gtest_main 与
        # fmt::fmt-header-only 两个目标（详见模块 docstring 第 3 条）
        gtest = self.dependencies["gtest"]
        fmt_dep = self.dependencies["fmt"]
        tc.cache_variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.cache_variables["fmt_DIR"] = os.path.join(
            fmt_dep.package_folder, "lib", "cmake", "fmt"
        ).replace("\\", "/")

        # CMake「Code Injection」：把 fmt / nlohmann_json 头目录按系统 include
        # 路径注入根工程作用域（上游 test/CMakeLists.txt 没给这些目标接线），
        # 并去掉 -DNDEBUG 让上游 assert() 检查点真实生效（docstring 第 2/4 条）。
        nlohmann = self.dependencies["nlohmann_json"]
        inject = os.path.join(self.generators_folder, "copypp-upstream-includes.cmake")
        with open(inject, "w", encoding="utf-8") as fh:
            fh.write(
                "# 生成文件（CMake CMAKE_PROJECT_INCLUDE 注入点），非上游源码、不入库。\n"
                "# 作用：把 Conan 依赖的 fmt / nlohmann_json 头目录并入根工程 include 路径，\n"
                "# 等价于上游作者机器上的 /usr/include；并取消 -DNDEBUG 使 assert() 生效。\n"
                'include_directories("{}" "{}")\n'
                "add_compile_options(-UNDEBUG)\n".format(
                    os.path.join(fmt_dep.package_folder, "include").replace("\\", "/"),
                    os.path.join(nlohmann.package_folder, "include").replace("\\", "/"),
                )
            )
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = inject
        tc.generate()

    # ── 构建 + 上游测试（R51 上游测试三步法）─────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info(
                "Cross-building: upstream copypp tests were built but not executed"
            )

    def _run_upstream_tests(self):
        """逐一执行 7 个上游 gtest 二进制并如实计数（任一非零即构建失败）。

        计数只取 gtest 运行期汇总行（``[==========] N tests ... ran.`` /
        ``[  PASSED  ] N tests.``），与源码宏清点互为候选数法的两个口径。
        """
        binaries = {}
        for path in sorted(Path(self.build_folder).rglob("*")):
            if path.is_file() and path.name in _UPSTREAM_TEST_BINARIES:
                binaries.setdefault(path.name, str(path))
        missing = [n for n in _UPSTREAM_TEST_BINARIES if n not in binaries]
        if missing:
            raise ConanException(
                "upstream test binary(s) not produced by the build: " + ", ".join(missing)
            )

        executed = 0
        passed = 0
        per_binary = {}
        for name in _UPSTREAM_TEST_BINARIES:
            outfile = os.path.join(self.build_folder, name + ".gtest.txt")
            # stdout+stderr 落盘后回显：既能在日志里看到原始输出，也便于计数
            self.run(
                f'"{binaries[name]}" > "{outfile}" 2>&1; rc=$?; cat "{outfile}"; exit $rc',
                env="conanrun",
            )
            text = Path(outfile).read_text(encoding="utf-8", errors="replace")
            m_run = re.search(r"\[==========\] (\d+) tests? from .*? ran\.", text)
            m_pass = re.search(r"\[  PASSED  \] (\d+) tests?\.", text)
            if not m_run or not m_pass:
                raise ConanException(
                    f"cannot parse GoogleTest summary from {name} output"
                )
            run_n, pass_n = int(m_run.group(1)), int(m_pass.group(1))
            if run_n != pass_n:
                raise ConanException(
                    f"{name}: {run_n} tests ran but only {pass_n} passed"
                )
            per_binary[name] = run_n
            executed += run_n
            passed += pass_n

        # 候选口径 1：源码宏数（R51 第一步）
        declared = 0
        test_dir = Path(self.source_folder) / "test"
        for src in sorted(test_dir.glob("*.cpp")):
            declared += len(
                re.findall(r"(?m)^\s*TEST(?:_F|_P)?\s*\(",
                           src.read_text(encoding="utf-8", errors="replace"))
            )

        result = {
            "status": "passed",
            "framework": "gtest",
            "source_declared_total": declared,
            "executed": executed,
            "passed": passed,
            "failed": executed - passed,
            "skipped": 0,
            "binaries": per_binary,
        }
        if executed != declared:
            result["note"] = (
                f"declared {declared} vs executed {executed}: difference must be "
                "attributed in the PR body"
            )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        self.output.info(
            f"[upstream-tests] {executed}/{executed} gtest 用例通过 "
            f"(源码宏 {declared} / 框架注册 {executed})"
        )

    # ── 打包：只交付头与许可证（header-only）────────────────────────────
    def package(self):
        copy(
            self,
            "*.hh",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "copypp")
        self.cpp_info.set_property("cmake_target_name", "icurve::copypp")
        self.cpp_info.set_property("pkg_config_name", "copypp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
