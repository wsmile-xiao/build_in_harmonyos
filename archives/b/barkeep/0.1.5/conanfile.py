#!/usr/bin/env python3
"""Conan recipe for barkeep 0.1.5 — header-only C++ 进度条/动画显示库。

交付物 = 单头文件 ``barkeep/barkeep.h``（``package_type="header-library"``、
``package_id`` 清空为单一 ID）。上游没有「库编译」阶段，但自带 Catch2 测试树
``tests/{test,test-fmtlib,test-stdfmt}.cpp``：本配方在 ``build()`` 内按上游 README
「No tooling」给出的编译口径（``-std=c++20 -pthread -I./``）直接编译三个测试翻译
单元并**真实运行**，按 Catch2 汇总行如实计数，任一测试非零退出即构建失败。
**不修改任何上游测试代码**（conandata ``patches: {}``，上游文件零改动）。

测试期依赖（``build_requirements()`` 里的 ``test_requires``，不进交付依赖）：
  * ``catch2/2.13.10`` —— 上游 ``#include <catch2/catch.hpp>``（Catch2 v2 单头 API，
    与上游 git 子模块 ``subprojects/Catch2_``（branch v2.x）同族）
  * ``fmt/11.1.3`` —— ``tests/test-fmtlib.cpp`` 自带 ``#define FMT_HEADER_ONLY``
    （仅用头文件、不链接），上游 meson wrap 钉 fmt 11.0.1，制品仓取最接近可用版

C++20 口径：上游 ``meson.build`` ``default_options: cpp_std=c++20``、``Makefile``
``FLAGS=-std=c++20`` ⇒ 测试编译命令行显式 ``-std=c++20``。配方**不改**
``settings.compiler.cppstd``：CI profile 是 ``cppstd=17``，且 ohpcd 制品仓的
``fmt/11.1.3`` 只提供 ``cppstd=17`` 二进制，而 CI ``conan create`` 只允许重建本包
（``--build=barkeep/*``），改 profile 会让 CI 取不到 fmt 二进制。

``tests/test-stdfmt.cpp`` 依赖 ``std::format``：OHOS SDK clang 15 + libc++ 15.0.4 的
``<format>`` 未实现 ``std::format/std::vformat/std::make_format_args``（设备探针
``no member named 'format' in namespace 'std'``）。该翻译单元按「OHOS 缺特性」记
**NOT_RUN**（编译错误签名匹配才允许跳过，其它编译错误一律失败），在日志与测试
申报中如实列出，**不写成通过**；其功能面由 ``test-fmtlib.cpp``（fmt 实现）等价覆盖。
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

# 上游 tests/meson.build sources 列表里的三个测试翻译单元（demo*.cpp 是演示程序，
# 不含任何断言，不计入测试用例）
_UPSTREAM_TEST_SOURCES = ("test.cpp", "test-fmtlib.cpp", "test-stdfmt.cpp")
# 只依赖标准库 + Catch2 的两个（可直接编译运行）
_RUNNABLE_TEST_SOURCES = ("test.cpp", "test-fmtlib.cpp")
# 上游测试声明宏（TEMPLATE_LIST_TEST_CASE 展开后注册数大于宏数，见 notes.md 口径表）
_CASE_MACRO_RE = re.compile(
    r"^\s*(TEST_CASE|TEMPLATE_TEST_CASE|TEMPLATE_LIST_TEST_CASE)\s*\("
)
# Catch2 v2 汇总行的两种形态（默认 reporter / -r compact）
_CATCH_SUMMARY_RE = re.compile(
    r"(?:All tests passed \((\d+) test cases? with (\d+) assertions\)"
    r"|Passed all (\d+) test cases with (\d+) assertions)"
)
# std::format 在 OHOS libc++ 上缺失的编译错误签名（仅命中这些才允许 NOT_RUN）
_STDFORMAT_ERROR_SIGNATURES = (
    "no member named 'vformat' in namespace 'std'",
    "no member named 'make_format_args' in namespace 'std'",
    "no member named 'format' in namespace 'std'",
    "'format' file not found",
)
_STDFORMAT_NOT_RUN_REASON = (
    "OHOS SDK libc++ 15.0.4 未实现 std::format（<format> 存在但缺 "
    "std::vformat/std::make_format_args），该翻译单元无法编译 ⇒ NOT_RUN；"
    "同一测试面由 tests/test-fmtlib.cpp（BARKEEP_ENABLE_FMT_FORMAT + "
    "FMT_HEADER_ONLY）等价覆盖"
)


class BarkeepConan(ConanFile):
    name = "barkeep"
    version = "0.1.5"
    description = "Terminal progress bar / animation display library (single header, C++20)"
    license = "Apache-2.0"
    homepage = "https://github.com/oir/barkeep"
    url = "https://github.com/oir/barkeep"
    topics = ("progress-bar", "terminal", "animation", "header-only", "cxx20")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # conandata patches 为空（上游零改动）⇒ 此调用是 no-op，但保留标准结构
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("barkeep targets Linux/OHOS terminals")

    def build_requirements(self):
        # 测试期依赖：不进 requirements()，不随包交付
        self.test_requires("catch2/2.13.10")
        self.test_requires("fmt/11.1.3")

    def generate(self):
        # 提供 conanbuild 环境（PATH / 工具链变量），self.run(env="conanbuild") 使用
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # patches 为空 ⇒ no-op（保留标准补丁应用位，G1 门禁要求存在该调用）
        apply_conandata_patches(self)

    # ── 工具方法 ──────────────────────────────────────────────────────────
    def _compiler(self) -> str:
        """R33：编译器一律来自 Conan conf，不用裸 shell 环境变量、不写死绝对路径。"""
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        return comp.get("cpp") or comp.get("c++") or "clang++"

    def _incdir(self, ref: str) -> str:
        dep = self.dependencies[ref]
        folder = Path(dep.package_folder)
        return str(folder / "include")

    @staticmethod
    def _declared_cases(src: Path) -> dict:
        """源码宏数（候选口径 1）：按翻译单元统计未被注释的用例声明宏。"""
        counts = {}
        for name in _UPSTREAM_TEST_SOURCES:
            path = src / "tests" / name
            if not path.is_file():
                continue
            counts[name] = sum(
                1 for line in path.read_text(encoding="utf-8").splitlines()
                if _CASE_MACRO_RE.match(line)
            )
        return counts

    @staticmethod
    def _parse_catch_summary(text: str) -> tuple:
        m = _CATCH_SUMMARY_RE.search(text)
        if not m:
            return (None, None)
        cases = m.group(1) or m.group(3)
        assertions = m.group(2) or m.group(4)
        return (int(cases), int(assertions))

    # ── 构建与上游测试 ────────────────────────────────────────────────────
    def build(self):
        src = Path(self.source_folder)
        out = Path(self.build_folder)
        out.mkdir(parents=True, exist_ok=True)

        cxx = self._compiler()
        # 上游 Makefile FLAGS：-std=c++20 -pthread；设备无 lcov/gcov 覆盖率链路，
        # 上游 DEBUG_FLAGS 里的 --coverage 不适用，保留 -O0（上游测试目标亦为非优化）。
        common = ["-O0", "-std=c++20", "-pthread",
                  f'-I"{src}"', f'-I"{self._incdir("catch2")}"']
        fmt_flags = [f'-I"{self._incdir("fmt")}"']

        declared = self._declared_cases(src)
        declared_total = sum(declared.values())
        runnable_declared = sum(declared.get(n, 0) for n in _RUNNABLE_TEST_SOURCES)

        binaries, not_run = {}, {}
        executed = passed = assertions = 0

        for name in _UPSTREAM_TEST_SOURCES:
            unit = src / "tests" / name
            if not unit.is_file():
                raise ConanException(f"upstream test source missing: tests/{name}")
            exe = out / name.replace(".cpp", ".out")
            cmd_flags = list(common)
            if name == "test-fmtlib.cpp":
                cmd_flags += fmt_flags
            compile_cmd = (
                f'"{cxx}" {" ".join(cmd_flags)} "{unit}" -o "{exe}"'
            )

            if name in _RUNNABLE_TEST_SOURCES:
                self.run(compile_cmd, env="conanbuild")
            else:
                # test-stdfmt.cpp：需要 std::format。仅在编译错误**签名匹配**
                # 「OHOS libc++ 缺 std::format」时记 NOT_RUN，其它编译错误照常失败；
                # 若工具链将来支持 std::format（编译通过），则照常运行、不留特殊分支。
                cerr_log = out / f"{name}.compile.log"
                with cerr_log.open("w", encoding="utf-8") as fh:
                    rc = self.run(compile_cmd, env="conanbuild",
                                  ignore_errors=True, stdout=fh, stderr=fh)
                text = cerr_log.read_text(encoding="utf-8", errors="replace")
                self.output.info(f"--- compile tests/{name} rc={rc} ---\n{text}")
                if rc != 0:
                    if not any(sig in text for sig in _STDFORMAT_ERROR_SIGNATURES):
                        raise ConanException(
                            f"tests/{name} failed to compile for an unrelated reason:\n{text}"
                        )
                    not_run[name] = _STDFORMAT_NOT_RUN_REASON
                    self.output.warning(
                        f"NOT_RUN tests/{name}: {_STDFORMAT_NOT_RUN_REASON}"
                    )
                    continue

            if not can_run(self):
                self.output.info(f"Cross-building: {exe.name} built but not executed")
                continue

            run_log = out / f"{exe.stem}.log"
            # 保留原文并回显到 conan/CI 日志（CI L1b 依赖编译与运行痕迹）
            self.run(
                f'"{exe}" -r compact > "{run_log}" 2>&1; rc=$?; cat "{run_log}"; exit $rc',
                env="conanbuild",
            )
            text = run_log.read_text(encoding="utf-8", errors="replace")
            cases, asserts_ = self._parse_catch_summary(text)
            if cases is None:
                raise ConanException(
                    f"cannot parse Catch2 summary from tests/{name} output:\n{text}"
                )
            binaries[exe.name] = cases
            executed += cases
            passed += cases
            assertions += asserts_

        result = {
            "status": "passed" if not not_run else "passed_with_not_run",
            "framework": "catch2",
            "source_declared_total": declared_total,
            "source_declared_by_file": declared,
            "source_declared_runnable": runnable_declared,
            "executed": executed,
            "passed": passed,
            "failed": 0,
            "skipped": 0,
            "not_run": sum(1 for _ in not_run),
            "assertions": assertions,
            "binaries": binaries,
            "not_run_sources": not_run,
        }
        if not_run:
            result["note"] = (
                "tests/test-stdfmt.cpp 未编译运行（OHOS libc++ 缺 std::format），"
                "其源码宏不计入 executed，差额在 PR 正文逐条归因"
            )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        copy(self, "barkeep/barkeep.h",
             src=self.source_folder,
             dst=str(Path(self.package_folder) / "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=str(Path(self.package_folder) / "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "barkeep")
        self.cpp_info.set_property("cmake_target_name", "barkeep::barkeep")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
