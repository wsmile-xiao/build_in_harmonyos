#!/usr/bin/env python3
"""Conan recipe for kitten 0.1.0 — header-only C++17 monad-like composition library.

交付物 = ``include/kitten/**.h`` 头文件树（``package_type="header-library"``、
``package_id()`` 清空为单一 ID）。上游没有库编译阶段（根 ``CMakeLists.txt`` 是
``add_library(... INTERFACE)``），但自带 Catch2 v2 测试树 ``tests/``（5 个翻译单元
编进 1 个 ``kitten_tests`` 可执行文件，上游 ``tests/CMakeLists.txt`` 同样只注册这
一个目标）。本配方在 ``build()`` 内按上游 ``tests/CMakeLists.txt`` 的编译口径直调
编译器（``-Wall -Wextra -Werror -ansi -pedantic`` + ``cxx_std_17``，上游
``-ansi`` 在 ``target_compile_features(cxx_std_17)`` 之后被 ``-std=c++17`` 取代，
故命令行按 ``-ansi`` 后置 ``-std=c++17`` 复现同一结果）编译并**真实运行**，按
Catch2 汇总行如实计数，且与源码 ``SCENARIO`` 声明数交叉核对，任一不符或非零退出
即 ``ConanException`` 构建失败。

**上游测试用例零修改**：唯一补丁落在产品头 ``include/kitten/instances/sequence_container.h``
（SFINAE 守卫从「模板身份」改为「实例化类型」，见 conandata ``patches`` 与
``notes.md``），4 个 ``SCENARIO`` 全部原样运行通过。

测试期依赖（``build_requirements()`` 里的 ``test_requires``，不进交付依赖）：
  * ``catch2/2.13.10`` —— 上游 ``#include <catch2/catch.hpp>``（Catch2 v2 单头 API）。
    该包在 ohpcd 制品仓为 ``info.clear()`` 单一包 ID（``da39a3ee…``），任意 profile 可得。
"""

import json
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游 tests/CMakeLists.txt add_executable(kitten_tests ...) 的全部源文件
# （main.cpp 定义 CATCH_CONFIG_MAIN；四个 *_test.cpp 各含 1 个 SCENARIO）
_UPSTREAM_TEST_SOURCES = (
    "main.cpp",
    "function_test.cpp",
    "optional_test.cpp",
    "sequence_container_test.cpp",
    "variant_test.cpp",
)
# 上游用例声明宏（Catch2 BDD 形态为 SCENARIO；候选口径 1）
_CASE_MACRO_RE = re.compile(r"^\s*(SCENARIO|TEST_CASE)\s*\(")
# Catch2 v2 汇总行两种形态：-r compact 与默认 reporter
_CATCH_SUMMARY_RES = (
    re.compile(r"Passed all (\d+) test cases? with (\d+) assertions"),
    re.compile(r"All tests passed \((\d+) assertions in (\d+) test cases?\)"),
)


class KittenConan(ConanFile):
    name = "kitten"
    version = "0.1.0"
    description = (
        "A simple library that introduces monad-like types to simplify composition "
        "for the modern C++ programmer (header-only, C++17)"
    )
    license = "MIT"
    homepage = "https://github.com/rvarago/kitten"
    url = "https://github.com/rvarago/kitten"
    topics = ("composition", "monads", "category-theory", "declarative-programming", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # conandata 有 1 个补丁 ⇒ 导出 patches/ 目录（G1 门禁要求该调用存在）
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("kitten targets Linux/OHOS")

    def build_requirements(self):
        # 测试期依赖：不进 requirements()，不随包交付
        self.test_requires("catch2/2.13.10")

    def generate(self):
        # 提供 conanbuild 环境（PATH / 工具链变量），self.run(env="conanbuild") 使用
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ── 工具方法 ──────────────────────────────────────────────────────────
    def _compiler(self) -> str:
        """R33：编译器来自 Conan conf，不用裸 shell 环境变量、不写死绝对路径。"""
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        return comp.get("cpp") or comp.get("c++") or "clang++"

    def _incdir(self, ref: str) -> str:
        dep = self.dependencies[ref]
        return str(Path(dep.package_folder) / "include")

    @staticmethod
    def _declared_cases(src: Path) -> int:
        """源码宏数（候选口径 1）：逐翻译单元统计未被注释的用例声明宏。"""
        total = 0
        for name in _UPSTREAM_TEST_SOURCES:
            path = src / "tests" / name
            if not path.is_file():
                continue
            total += sum(
                1 for line in path.read_text(encoding="utf-8").splitlines()
                if _CASE_MACRO_RE.match(line)
            )
        return total

    @staticmethod
    def _parse_catch_summary(text: str):
        for i, rx in enumerate(_CATCH_SUMMARY_RES):
            m = rx.search(text)
            if not m:
                continue
            if i == 0:  # compact: (cases, assertions)
                return int(m.group(1)), int(m.group(2))
            # default: (assertions, cases)
            return int(m.group(2)), int(m.group(1))
        return None, None

    # ── 构建与上游测试 ────────────────────────────────────────────────────
    def build(self):
        src = Path(self.source_folder)
        out = Path(self.build_folder)
        out.mkdir(parents=True, exist_ok=True)

        cxx = self._compiler()
        declared = self._declared_cases(src)
        if declared <= 0:
            raise ConanException("upstream test sources declare 0 test cases — counting is broken")

        # 上游 tests/CMakeLists.txt 口径：-Wall -Wextra -Werror -ansi -pedantic +
        # target_compile_features(cxx_std_17)。-ansi 之后显式 -std=c++17 复现上游
        # 「cxx_std_17 覆盖 -ansi」的同一结果。
        flags = ["-O0", "-Wall", "-Wextra", "-Werror", "-ansi", "-pedantic", "-std=c++17",
                 f'-I"{src / "include"}"', f'-I"{self._incdir("catch2")}"']
        units = " ".join(f'"{src / "tests" / name}"' for name in _UPSTREAM_TEST_SOURCES)
        exe = out / "kitten_tests"
        compile_cmd = f'"{cxx}" {" ".join(flags)} {units} -o "{exe}"'
        self.output.info(f"compile upstream tests: {compile_cmd}")
        self.run(compile_cmd, env="conanbuild")

        if not can_run(self):
            self.output.info(f"Cross-building: {exe.name} built but not executed")
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    {"status": "built_not_run", "framework": "catch2",
                     "source_declared_total": declared, "executed": 0},
                    ensure_ascii=False))
            return

        run_log = out / "kitten_tests.log"
        # 保留原文并回显到 conan/CI 日志（CI L1b 依赖编译与运行痕迹）
        self.run(
            f'"{exe}" -r compact > "{run_log}" 2>&1; rc=$?; cat "{run_log}"; exit $rc',
            env="conanbuild",
        )
        text = run_log.read_text(encoding="utf-8", errors="replace")
        cases, assertions = self._parse_catch_summary(text)
        if cases is None:
            raise ConanException(f"cannot parse Catch2 summary from test output:\n{text}")
        if cases == 0:
            raise ConanException("All 0 tests passed — Catch2 registered nothing, refusing green")
        if cases != declared:
            raise ConanException(
                f"test case count mismatch: source declares {declared}, framework ran {cases}\n{text}"
            )

        result = {
            "status": "passed",
            "framework": "catch2",
            "source_declared_total": declared,
            "executed": cases,
            "passed": cases,
            "failed": 0,
            "skipped": 0,
            "not_run": 0,
            "assertions": assertions,
            "binaries": {exe.name: cases},
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        copy(self, "*.h",
             src=str(Path(self.source_folder) / "include"),
             dst=str(Path(self.package_folder) / "include"),
             keep_path=True)
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=str(Path(self.package_folder) / "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # 消费者目标名跟上游 README「find_package(kitten) + target_link_libraries(…
        # rvarago::kitten)」与上游根 CMakeLists 的 install(EXPORT … NAMESPACE rvarago::)
        # 一致，也与 conan-center-index 的 kitten 配方同名先例一致。
        self.cpp_info.set_property("cmake_file_name", "kitten")
        self.cpp_info.set_property("cmake_target_name", "rvarago::kitten")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
